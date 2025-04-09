# services/blockchain/transactions.py
import logging
import time
from typing import Dict, Any, Optional, Tuple, Union

from web3 import Web3
from web3.types import TxParams, TxReceipt, Wei
from eth_account.datastructures import SignedTransaction
from ...core.config import settings
from .nonce_manager import NonceManager
from .rate_limiter import RateLimiter

# Configure logging
logger = logging.getLogger(__name__)

class TransactionManager:
    def __init__(self, w3: Web3, account: Any):
        self.w3 = w3
        self.account = account
        self.chain_id = settings.CHAIN_ID
        
        # Initialize nonce manager and rate limiter
        self.nonce_manager = NonceManager(self.w3, self.account.address)
        self.rate_limiter = RateLimiter(max_requests=5, refill_rate=1.0, refill_interval=1.0)
        
        # Transaction tracking
        self.pending_transactions = {}
        self.transaction_details = {}
    
    def get_eip1559_fees(self, latest_block=None) -> Tuple[int, int, int, bool]:
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
    
    def simulate_transaction(self, tx_data: TxParams) -> None:
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
        except Exception as e:
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
    
    def send_transaction(self, tx_dict: dict, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a transaction with enhanced error handling and tracking"""
        tx_hash = None
        try:
            # Add chain ID and nonce if not provided
            if 'chainId' not in tx_dict:
                tx_dict['chainId'] = self.chain_id
            
            if 'nonce' not in tx_dict:
                # Get the latest nonce for this account
                tx_dict['nonce'] = self.w3.eth.get_transaction_count(self.account.address)
            
            # Log the transaction details before sending
            function_name = details.get('function', 'unknown') if details else 'unknown'
            logger.info(f"Sending transaction for function: {function_name}")
            logger.info(f"Transaction details:\n" + 
                       f"From: {tx_dict.get('from', self.account.address)}\n" +
                       f"To: {tx_dict.get('to', 'Not specified')}\n" +
                       f"Gas: {tx_dict.get('gas', 'Not specified')}\n" +
                       f"Gas Price: {Web3.from_wei(tx_dict.get('gasPrice', 0), 'gwei')} gwei\n" +
                       f"Nonce: {tx_dict.get('nonce', 'Not specified')}")
            
            start_time = time.time()
            
            # Sign the transaction with the account's private key
            logger.info("Signing transaction...")
            signed_tx = self.account.sign_transaction(tx_dict)
            logger.debug(f"Transaction signed successfully")
            
            try:
                # Use rate limiter to prevent 429 errors when sending raw transaction
                def send_tx():
                    # Make sure we're using the correct property (raw_transaction)
                    if hasattr(signed_tx, 'rawTransaction'):
                        raw_tx = signed_tx.rawTransaction
                    elif hasattr(signed_tx, 'raw_transaction'):
                        raw_tx = signed_tx.raw_transaction
                    else:
                        # If neither attribute exists, try accessing it as a dictionary
                        try:
                            raw_tx = signed_tx['rawTransaction']
                        except (TypeError, KeyError):
                            # Last resort: convert to dict and look for any key that might contain the raw tx
                            signed_dict = dict(signed_tx)
                            for key in signed_dict:
                                if 'raw' in str(key).lower():
                                    raw_tx = signed_dict[key]
                                    break
                            else:
                                raise ValueError(f"Cannot find raw transaction in {signed_tx}")
                    
                    return self.w3.eth.send_raw_transaction(raw_tx).hex()
                
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
                    "gas_limit": tx_dict.get('gas', 0),
                    "gas_price": tx_dict.get('gasPrice', 0),
                    "nonce": tx_dict.get('nonce', 0),
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
                logger.info(f"Gas used: {tx_receipt.gasUsed} / {tx_dict.get('gas', 0)} ({tx_receipt.gasUsed / tx_dict.get('gas', 1) * 100:.1f}%)")
                logger.info(f"Transaction mined in {duration_ms}ms")
                
                # Update transaction details
                if tx_hash in self.transaction_details:
                    self.transaction_details[tx_hash].update({
                        "status": status,
                        "block_number": tx_receipt.blockNumber,
                        "gas_used": tx_receipt.gasUsed,
                        "transaction_found": True,
                        "error": None if status == "confirmed" else "Transaction execution failed",
                        "duration_ms": duration_ms
                    })
                
                # Prepare a comprehensive result object
                result = {
                    'tx_hash': tx_hash,
                    'block': tx_receipt.blockNumber,
                    'status': 'success' if status == "confirmed" else 'failed',
                    'gas_used': tx_receipt.gasUsed,
                    'gas_limit': tx_dict.get('gas', 0),
                    'gas_efficiency': f"{tx_receipt.gasUsed / tx_dict.get('gas', 1) * 100:.1f}%",
                    'duration_ms': duration_ms,
                    'timestamp': int(time.time())
                }
                
                # Add transaction details if provided
                if details:
                    result['details'] = details
                    
                return result
            except Exception as e:
                error_message = str(e)
                logger.error(f"Transaction failed: {error_message}")
                
                # Store error information in transaction details
                if tx_hash and tx_hash in self.transaction_details:
                    self.transaction_details[tx_hash].update({
                        "status": "failed",
                        "error": error_message
                    })
                
                # Categorize common errors for better debugging
                error_category = "unknown"
                if "nonce too low" in error_message.lower():
                    error_category = "nonce_too_low"
                elif "insufficient funds" in error_message.lower():
                    error_category = "insufficient_funds"
                elif "gas required exceeds allowance" in error_message.lower():
                    error_category = "gas_limit_exceeded"
                elif "already known" in error_message.lower():
                    error_category = "already_known"
                elif "timeout" in error_message.lower():
                    error_category = "timeout"
                elif "rate limit" in error_message.lower():
                    error_category = "rate_limited"
                
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
            logger.error(f"Unexpected error in send_transaction: {error_message}")
            
            return {
                'status': 'error',
                'error': error_message,
                'error_category': 'unexpected_error',
                'tx_hash': tx_hash,
                'timestamp': int(time.time()),
                'details': details
            }
    
    def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        """Get the status of a transaction"""
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
            
            # Get block timestamp if available
            timestamp = None
            try:
                block = self.w3.eth.get_block(tx_receipt.blockNumber)
                if block and hasattr(block, 'timestamp'):
                    timestamp = block.timestamp
            except Exception:
                pass
            
            return {
                'status': status,
                'tx_hash': tx_hash,
                'transaction_found': True,
                'block_number': tx_receipt.blockNumber,
                'gas_used': tx_receipt.gasUsed,
                'from': tx_data['from'],
                'to': tx_data['to'],
                'nonce': tx_data['nonce'],
                'timestamp': timestamp
            }
        except Exception as e:
            logger.error(f"Error getting transaction status: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'tx_hash': tx_hash,
                'transaction_found': False
            }