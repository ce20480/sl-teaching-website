"""
Base contract service for blockchain interactions.
This module provides a base class for services that interact with blockchain contracts.
"""
import logging
import time
import functools
from typing import Any, Dict, Optional, Tuple, Callable, TypeVar, cast

from web3 import Web3
from web3.contract import Contract
from web3.exceptions import ContractLogicError
from web3.types import TxParams

from ...core.config import settings
from .nonce_manager import NonceManager
from .rate_limiter import RateLimiter

# Configure logging
logger = logging.getLogger(__name__)

# Type variables for the retry decorator
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

# Retry decorator with exponential backoff for handling transient errors
def retry_with_backoff(max_retries: int = 3, initial_backoff: float = 0.5, backoff_factor: float = 2):
    """Retry decorator with exponential backoff for handling transient errors"""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            retries = 0
            current_backoff = initial_backoff
            
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded. Last error: {str(e)}")
                        raise
                    
                    # Only retry on specific errors that might be transient
                    error_msg = str(e).lower()
                    if any(err in error_msg for err in ["nonce too low", "replacement transaction underpriced", 
                                                       "already known", "connection", "timeout", "rate limit"]):
                        logger.warning(f"Retrying after error: {str(e)} (retry {retries}/{max_retries})")
                        time.sleep(current_backoff)
                        current_backoff *= backoff_factor
                    else:
                        # Don't retry on other errors
                        logger.error(f"Non-retryable error: {str(e)}")
                        raise
        
        return cast(F, wrapper)
    return decorator


class BaseContractService:
    """Base class for blockchain contract services"""
    
    def __init__(self, w3: Web3, account: Any, contract: Contract):
        """
        Initialize the base contract service.
        
        Args:
            w3: Web3 instance
            account: Account to use for transactions
            contract: Contract instance
        """
        self.w3 = w3
        self.account = account
        self.contract = contract
        
        # Initialize nonce manager and rate limiter
        self.nonce_manager = NonceManager(self.w3, self.account.address)
        self.rate_limiter = RateLimiter(max_requests=5, refill_rate=1.0, refill_interval=1.0)
        
        # Transaction tracking
        self.pending_transactions = {}
        self.transaction_details = {}
    
    def _simulate_transaction(self, tx_data: TxParams) -> None:
        """Simulate a transaction to check if it would succeed"""
        try:
            # Create a copy of the transaction data for simulation
            call_data = tx_data.copy()
            
            # For call, we don't need these parameters
            for param in ['chainId', 'gas', 'gasPrice', 'nonce', 'maxFeePerGas', 'maxPriorityFeePerGas']:
                if param in call_data:
                    del call_data[param]
            
            # Use eth_call to simulate the transaction
            self.w3.eth.call(call_data)
            logger.info("Transaction simulation successful")
        except ContractLogicError as e:
            # Extract the revert reason if available
            revert_reason = str(e)
            logger.error(f"Transaction would fail: {revert_reason}")
            
            # Log transaction details for debugging
            logger.error("Transaction details:")
            logger.error(f"  From: {tx_data.get('from', 'Not specified')}")
            logger.error(f"  To: {tx_data.get('to', 'Not specified')}")
            logger.error(f"  Gas: {tx_data.get('gas', 'Not specified')}")
            logger.error(f"  Gas Price: {Web3.from_wei(tx_data.get('gasPrice', 0), 'gwei')} gwei")
            logger.error(f"  Value: {Web3.from_wei(tx_data.get('value', 0), 'ether')} ETH")
            logger.error(f"  Nonce: {tx_data.get('nonce', 'Not specified')}")
            
            # Check for common error patterns and provide more specific feedback
            if "gas required exceeds allowance" in revert_reason:
                logger.error("Gas estimation failed. The transaction might be reverting or gas limit is too low.")
                # Try to get block gas limit for reference
                try:
                    block_gas_limit = self.w3.eth.get_block('latest').gasLimit
                    logger.error(f"Current block gas limit: {block_gas_limit}")
                except Exception as gas_error:
                    logger.error(f"Could not get block gas limit: {str(gas_error)}")
            elif "insufficient funds" in revert_reason.lower():
                account_balance = self.w3.eth.get_balance(self.account.address)
                logger.error(f"Insufficient funds. Account balance: {Web3.from_wei(account_balance, 'ether')} ETH")
            elif "nonce too low" in revert_reason.lower():
                current_nonce = self.w3.eth.get_transaction_count(self.account.address)
                logger.error(f"Nonce too low. Current account nonce: {current_nonce}, Transaction nonce: {tx_data.get('nonce')}")
            elif "already known" in revert_reason.lower():
                logger.warning("Transaction already in the mempool. This is not an error, but a duplicate transaction.")
            
            raise ValueError(f"Transaction would fail: {revert_reason}")
        except Exception as e:
            logger.error(f"Error simulating transaction: {str(e)}")
            # Log any additional context that might be helpful
            try:
                logger.error(f"Current network status - Latest block: {self.w3.eth.block_number}")
                logger.error(f"Current gas price: {Web3.from_wei(self.w3.eth.gas_price, 'gwei')} gwei")
            except Exception as context_error:
                logger.error(f"Could not get additional context: {str(context_error)}")
            
            raise ValueError(f"Transaction simulation failed: {str(e)}")
    
    def _get_block_timestamp(self, block_number: int) -> int:
        """Get the timestamp of a block"""
        try:
            block = self.w3.eth.get_block(block_number)
            return block.timestamp if block and hasattr(block, 'timestamp') else 0
        except Exception as e:
            logger.debug(f"Could not get block timestamp for block {block_number}: {str(e)}")
            return 0
    
    def _get_eip1559_fees(self, latest_block=None) -> Tuple[int, int, int, bool]:
        """Calculate EIP-1559 transaction fees
        
        Returns:
            Tuple containing (max_fee_per_gas, max_priority_fee_per_gas, base_fee, is_eip1559_supported)
        """
        use_eip1559 = False
        max_fee = 0
        priority_fee = 0
        base_fee = 0
        
        try:
            # Get latest block if not provided
            if not latest_block:
                latest_block = self.w3.eth.get_block('latest')
                
            # Check if the network supports EIP-1559
            if 'baseFeePerGas' in latest_block:
                use_eip1559 = True
                base_fee = latest_block.get('baseFeePerGas', 0)
                
                # Set priority fee to 1 gwei or use a dynamic calculation based on network conditions
                priority_fee = self.w3.to_wei('1', 'gwei')  # 1 gwei priority fee
                
                # Calculate max fee as 2x base fee + priority fee
                # This gives us room for base fee increases while still getting included
                max_fee = base_fee * 2 + priority_fee
                
                logger.info(f"EIP-1559 fees calculated: base_fee={Web3.from_wei(base_fee, 'gwei')} gwei, "
                           f"priority_fee={Web3.from_wei(priority_fee, 'gwei')} gwei, "
                           f"max_fee={Web3.from_wei(max_fee, 'gwei')} gwei")
            else:
                logger.info("Network does not support EIP-1559, using legacy transaction type")
        except Exception as e:
            logger.warning(f"Error calculating EIP-1559 fees: {str(e)}. Will use legacy transactions.")
            use_eip1559 = False
            
        return max_fee, priority_fee, base_fee, use_eip1559
    
    @retry_with_backoff(max_retries=3)
    def _send_transaction(self, tx_data: TxParams, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Helper method to send a transaction and handle the response with retries"""
        tx_hash = None
        try:
            # Add nonce management
            if 'nonce' not in tx_data:
                # Get the latest nonce for this account
                tx_data['nonce'] = self.w3.eth.get_transaction_count(self.account.address)
            
            # Log the transaction details before sending
            function_name = details.get('function', 'unknown') if details else 'unknown'
            logger.info(f"Sending transaction for function: {function_name}")
            logger.info(f"Transaction details:\n" + 
                       f"From: {tx_data.get('from', self.account.address)}\n" +
                       f"To: {tx_data.get('to', 'Not specified')}\n" +
                       f"Gas: {tx_data.get('gas', 'Not specified')}\n" +
                       f"Gas Price: {Web3.from_wei(tx_data.get('gasPrice', 0), 'gwei')} gwei\n" +
                       f"Nonce: {tx_data.get('nonce', 'Not specified')}")
            
            start_time = time.time()
            
            # Sign the transaction with the account's private key
            logger.info("Signing transaction...")
            signed_tx = self.account.sign_transaction(tx_data)
            logger.debug(f"Transaction signed successfully")
            
            try:
                # Use rate limiter to prevent 429 errors when sending raw transaction
                def send_tx():
                    # Make sure we're using the correct property (raw_transaction)
                    return self.w3.eth.send_raw_transaction(signed_tx.raw_transaction).hex()
                
                # Execute the send_tx function with rate limiting
                tx_hash = self.rate_limiter.execute_with_rate_limit(send_tx)
                logger.info(f"Transaction sent with hash: {tx_hash}")
            except Exception as e:
                error_msg = f"Failed to send raw transaction: {str(e)}"
                logger.error(error_msg)
                
                # Check if this is a nonce error and handle it
                if "nonce" in str(e).lower() and "low" in str(e).lower():
                    logger.warning("Nonce too low error detected, handling with nonce manager")
                    new_nonce = self.nonce_manager.handle_nonce_error(str(e))
                    logger.info(f"Updated nonce to {new_nonce}, please retry the transaction")
                    
                    # Return a specific error that the API can handle for retries
                    return {
                        'status': 'error',
                        'error': error_msg,
                        'error_category': 'nonce_too_low',
                        'tx_hash': None,
                        'timestamp': int(time.time()),
                        'details': details
                    }
                elif "already known" in str(e).lower() or "already exists" in str(e).lower():
                    # Handle duplicate transaction
                    logger.warning("Transaction already in the mempool. This is not an error, but a duplicate transaction.")
                    # Try to extract the transaction hash from the error message
                    import re
                    hash_match = re.search(r'0x[a-fA-F0-9]{64}', str(e))
                    if hash_match:
                        tx_hash = hash_match.group(0)
                        logger.info(f"Extracted existing transaction hash: {tx_hash}")
                        # Continue with this hash
                    else:
                        # If we can't extract the hash, raise the error
                        raise ValueError(error_msg)
                else:
                    # For other errors, raise the exception
                    raise ValueError(error_msg)
            
            # Store initial transaction details before confirmation
            if details and 'address' in details:
                address = details['address']
                if address not in self.pending_transactions:
                    self.pending_transactions[address] = []
                self.pending_transactions[address].append(tx_hash)
                # Store initial transaction details
                self.transaction_details[tx_hash] = {
                    "address": address,
                    "function": details.get('function', 'unknown'),
                    "timestamp": int(time.time()),
                    "status": "pending",
                    "transaction_found": True,
                    "gas_limit": tx_data.get('gas', 0),
                    "gas_price": tx_data.get('gasPrice', 0),
                    "nonce": tx_data.get('nonce', 0),
                    "error": None
                }
            
            # Wait for transaction receipt with better error handling and rate limiting
            try:
                logger.info(f"Waiting for transaction {tx_hash} to be mined...")
                
                def get_receipt():
                    return self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                # Use rate limiter to prevent too many requests
                tx_receipt = self.rate_limiter.execute_with_rate_limit(get_receipt)
                end_time = time.time()
                
                # Calculate transaction duration
                duration_ms = int((end_time - start_time) * 1000)
                
                # Update transaction status based on receipt status
                status = "confirmed" if tx_receipt.status == 1 else "failed"
                
                # Log detailed transaction information
                logger.info(f"Transaction {tx_hash} {status} in block {tx_receipt.blockNumber}")
                logger.info(f"Gas used: {tx_receipt.gasUsed} / {tx_data.get('gas', 0)} ({tx_receipt.gasUsed / tx_data.get('gas', 1) * 100:.1f}%)")
                logger.info(f"Transaction mined in {duration_ms}ms")
                
                if status == "failed":
                    # Try to get more information about the failure
                    try:
                        # Log transaction details for debugging
                        logger.error(f"Transaction {tx_hash} failed in block {tx_receipt.blockNumber}")
                        logger.error(f"Gas used: {tx_receipt.gasUsed} / {tx_data.get('gas', 0)}")
                        logger.error(f"From: {tx_data.get('from', 'unknown')}")
                        logger.error(f"Nonce: {tx_data.get('nonce', 'unknown')}")
                        
                        # Try to get transaction data for more details
                        tx_data_from_chain = self.w3.eth.get_transaction(tx_hash)
                        logger.error(f"Transaction data from chain: {tx_data_from_chain}")
                        
                        # Check if we used all gas - likely an error in execution
                        if tx_receipt.gasUsed >= (tx_data.get('gas', 0) * 0.95):  # Used more than 95% of gas limit
                            logger.error(f"Transaction used almost all gas ({tx_receipt.gasUsed}/{tx_data.get('gas', 0)}). " +
                                        "This usually indicates a runtime error or out of gas condition.")
                            
                            # Try to get transaction trace if available
                            try:
                                # This only works if the node supports debug_traceTransaction
                                if hasattr(self.w3, 'debug') and hasattr(self.w3.debug, 'traceTransaction'):
                                    trace = self.w3.debug.traceTransaction(tx_hash)
                                    logger.error(f"Transaction trace: {trace}")
                                else:
                                    # Alternative method using provider directly
                                    try:
                                        trace_result = self.w3.provider.make_request("debug_traceTransaction", [tx_hash, {"tracer": "callTracer"}])
                                        if trace_result and 'result' in trace_result:
                                            logger.error(f"Transaction trace: {trace_result['result']}")
                                    except Exception as alt_trace_err:
                                        logger.debug(f"Could not get transaction trace using provider: {str(alt_trace_err)}")
                            except Exception as trace_error:
                                logger.error(f"Could not get transaction trace: {str(trace_error)}")
                    except Exception as debug_error:
                        logger.error(f"Error getting debug information: {str(debug_error)}")
                        
                # Create a receipt placeholder if we don't have a real receipt
                if not tx_receipt:
                    tx_receipt = {
                        "blockNumber": 0,
                        "gasUsed": 0,
                        "status": 0
                    }
                
                # Update transaction details with more error information
                if tx_hash in self.transaction_details:
                    error_message = None
                    if status == "failed":
                        if isinstance(tx_receipt, dict):
                            error_message = "Error waiting for transaction receipt"
                            block_number = tx_receipt.get("blockNumber", 0)
                            gas_used = tx_receipt.get("gasUsed", 0)
                        else:
                            error_message = "Transaction execution failed on blockchain"
                            block_number = tx_receipt.blockNumber
                            gas_used = tx_receipt.gasUsed
                            
                            # Add more specific error information if available
                            if hasattr(tx_receipt, "gasUsed") and tx_receipt.gasUsed >= (tx_data.get('gas', 0) * 0.95):
                                error_message = "Transaction failed - likely out of gas or execution error"
                    else:
                        # Transaction was confirmed successfully
                        block_number = tx_receipt.blockNumber if not isinstance(tx_receipt, dict) else 0
                        gas_used = tx_receipt.gasUsed if not isinstance(tx_receipt, dict) else 0
                    
                    self.transaction_details[tx_hash].update({
                        "status": status,
                        "block_number": block_number,
                        "gas_used": gas_used,
                        "transaction_found": True,
                        "error": error_message,
                        "duration_ms": duration_ms
                    })
                
                # Keep only the last 10 transactions per address
                if details and 'address' in details:
                    address = details['address']
                    if address in self.pending_transactions and len(self.pending_transactions[address]) > 10:
                        old_tx = self.pending_transactions[address].pop(0)
                        if old_tx in self.transaction_details:
                            del self.transaction_details[old_tx]
                
                # Prepare a comprehensive result object with detailed transaction information
                result = {
                    'tx_hash': tx_hash,
                    'block': tx_receipt.blockNumber,
                    'status': 'success' if status == "confirmed" else 'failed',
                    'gas_used': tx_receipt.gasUsed,
                    'gas_limit': tx_data.get('gas', 0),
                    'gas_efficiency': f"{tx_receipt.gasUsed / tx_data.get('gas', 1) * 100:.1f}%",
                    'duration_ms': duration_ms,
                    'timestamp': int(time.time()),
                    'block_timestamp': self._get_block_timestamp(tx_receipt.blockNumber) if hasattr(tx_receipt, 'blockNumber') else None,
                    'transaction_index': tx_receipt.transactionIndex if hasattr(tx_receipt, 'transactionIndex') else 0
                }
                
                # Add transaction details if provided
                if details:
                    result['details'] = details
                    
                # Add gas price information based on transaction type
                if 'gasPrice' in tx_data:
                    result['gas_price'] = Web3.from_wei(tx_data['gasPrice'], 'gwei')
                    result['gas_price_wei'] = tx_data['gasPrice']
                elif 'maxFeePerGas' in tx_data:
                    result['max_fee_per_gas'] = Web3.from_wei(tx_data['maxFeePerGas'], 'gwei')
                    result['max_priority_fee_per_gas'] = Web3.from_wei(tx_data['maxPriorityFeePerGas'], 'gwei')
                    result['max_fee_per_gas_wei'] = tx_data['maxFeePerGas']
                    result['max_priority_fee_per_gas_wei'] = tx_data['maxPriorityFeePerGas']
                    result['transaction_type'] = 'EIP-1559'
                else:
                    result['gas_price'] = Web3.from_wei(self.w3.eth.gas_price, 'gwei')
                    
                # Add transaction logs if available
                if hasattr(tx_receipt, 'logs') and tx_receipt.logs:
                    try:
                        # Try to decode logs using contract events
                        decoded_logs = []
                        for log in tx_receipt.logs:
                            try:
                                # Try to decode each log using contract events
                                for event_name in self.contract.events:
                                    try:
                                        event = getattr(self.contract.events, event_name)
                                        decoded = event().process_log(log)
                                        if decoded:
                                            decoded_logs.append({
                                                'event': decoded.event,
                                                'args': {k: str(v) for k, v in decoded.args.items()}
                                            })
                                            break
                                    except Exception:
                                        continue
                            except Exception:
                                # If we can't decode this log, skip it
                                pass
                        
                        if decoded_logs:
                            result['decoded_logs'] = decoded_logs
                    except Exception as log_error:
                        logger.debug(f"Could not decode logs: {str(log_error)}")
                    
                if status == "confirmed":
                    logger.info(f"Transaction successful: {tx_hash}")
                else:
                    logger.error(f"Transaction execution failed: {tx_hash}")
                    result['error'] = "Transaction execution failed on blockchain"
                    
                return result
            except Exception as e:
                error_message = str(e)
                logger.error(f"Transaction failed: {error_message}")
                
                # Store error information in transaction details
                if tx_hash and details and 'address' in details:
                    address = details['address']
                    if tx_hash not in self.transaction_details:
                        if address not in self.pending_transactions:
                            self.pending_transactions[address] = []
                        self.pending_transactions[address].append(tx_hash)
                        self.transaction_details[tx_hash] = {
                            "address": address,
                            "function": details.get('function', 'unknown'),
                            "timestamp": int(time.time()),
                            "status": "failed",
                            "transaction_found": False,
                            "error": error_message
                        }
                    else:
                        self.transaction_details[tx_hash].update({
                            "status": "failed",
                            "error": error_message
                        })
                
                # Categorize common errors for better debugging
                error_category = "unknown"
                if "nonce too low" in error_message.lower():
                    error_category = "nonce_too_low"
                    current_nonce = self.w3.eth.get_transaction_count(self.account.address)
                    logger.error(f"Nonce too low - transaction might have been replaced. Current account nonce: {current_nonce}, Transaction nonce: {tx_data.get('nonce')}")
                elif "insufficient funds" in error_message.lower():
                    error_category = "insufficient_funds"
                    account_balance = self.w3.eth.get_balance(self.account.address)
                    estimated_cost = tx_data.get('gas', 21000) * tx_data.get('gasPrice', self.w3.eth.gas_price)
                    logger.error(f"Insufficient funds for transaction. Account balance: {Web3.from_wei(account_balance, 'ether')} ETH, Estimated cost: {Web3.from_wei(estimated_cost, 'ether')} ETH")
                elif "gas required exceeds allowance" in error_message.lower():
                    error_category = "gas_limit_exceeded"
                    logger.error(f"Gas estimation failed. The transaction might be reverting or gas limit is too low. Gas limit: {tx_data.get('gas')}")
                elif "already known" in error_message.lower():
                    error_category = "already_known"
                    logger.warning("Transaction already in the mempool. This is not an error, but a duplicate transaction.")
                elif "timeout" in error_message.lower():
                    error_category = "timeout"
                    logger.error("Transaction timed out. The network might be congested.")
                elif "rate limit" in error_message.lower():
                    error_category = "rate_limited"
                    logger.error("Rate limit exceeded. The RPC provider is throttling requests.")
                
                return {
                    'status': 'error',
                    'error': error_message,
                    'error_category': error_category,
                    'tx_hash': tx_hash,
                    'timestamp': int(time.time()),
                    'details': details
                }
        except Exception as e:
            error_message = str(e)
            logger.error(f"Unexpected error in _send_transaction: {error_message}")
            
            return {
                'status': 'error',
                'error': error_message,
                'error_category': 'unexpected_error',
                'tx_hash': tx_hash,
                'timestamp': int(time.time()),
                'details': details
            }
    
    def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        """
        Get the status of a transaction
        
        Args:
            tx_hash: Transaction hash to check
            
        Returns:
            dict: Transaction status and details
        """
        if not tx_hash:
            return {
                'status': 'error',
                'error': 'No transaction hash provided',
                'tx_hash': None
            }
        
        # Check if we have details for this transaction
        if tx_hash in self.transaction_details:
            # Return the stored details
            return {
                'status': self.transaction_details[tx_hash].get('status', 'unknown'),
                'tx_hash': tx_hash,
                **self.transaction_details[tx_hash]
            }
        
        # If we don't have details, try to get them from the blockchain
        try:
            # Check if the transaction exists
            tx_data = self.w3.eth.get_transaction(tx_hash)
            if not tx_data:
                return {
                    'status': 'error',
                    'error': 'Transaction not found',
                    'tx_hash': tx_hash,
                    'transaction_found': False
                }
            
            # Check if the transaction has been mined
            if tx_data.blockNumber is None:
                return {
                    'status': 'pending',
                    'tx_hash': tx_hash,
                    'transaction_found': True,
                    'from': tx_data['from'],
                    'to': tx_data['to'],
                    'nonce': tx_data['nonce']
                }
            
            # Get the transaction receipt
            tx_receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            if not tx_receipt:
                return {
                    'status': 'pending',
                    'tx_hash': tx_hash,
                    'transaction_found': True,
                    'block_number': tx_data.blockNumber,
                    'from': tx_data['from'],
                    'to': tx_data['to'],
                    'nonce': tx_data['nonce']
                }
            
            # Determine the status
            status = 'success' if tx_receipt.status == 1 else 'failed'
            
            return {
                'status': status,
                'tx_hash': tx_hash,
                'transaction_found': True,
                'block_number': tx_receipt.blockNumber,
                'gas_used': tx_receipt.gasUsed,
                'from': tx_data['from'],
                'to': tx_data['to'],
                'nonce': tx_data['nonce'],
                'timestamp': self._get_block_timestamp(tx_receipt.blockNumber)
            }
        except Exception as e:
            logger.error(f"Error getting transaction status: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'tx_hash': tx_hash,
                'transaction_found': False
            }
    
    def get_transactions(self, address: str) -> list:
        """
        Get recent transactions for an address
        
        Args:
            address: Ethereum address to check transactions for
            
        Returns:
            list: List of recent transactions
        """
        if not address:
            return []
        
        # Check if we have transactions for this address
        transactions = []
        if address in self.pending_transactions:
            tx_hashes = self.pending_transactions[address]
            for tx_hash in tx_hashes:
                if tx_hash in self.transaction_details:
                    transactions.append({
                        "tx_hash": tx_hash,
                        **self.transaction_details[tx_hash]
                    })
                
        return transactions
