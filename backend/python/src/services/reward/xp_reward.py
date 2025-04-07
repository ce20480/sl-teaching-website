# services/reward/xp_reward.py
import logging
import time
import functools
import asyncio
import json
import os
from enum import IntEnum
from typing import Any, Callable, Dict, Optional, TypeVar, cast, List

from web3 import Web3
from web3.exceptions import ContractLogicError
from web3.types import TxParams, TxReceipt

from ...services.blockchain.core import BlockchainService, get_blockchain_service
from ...services.blockchain.transactions import TransactionManager
from ...core.config import settings
from fastapi import Depends, HTTPException
from collections import defaultdict

# Configure logging
logger = logging.getLogger(__name__)

# Define ActivityType enum to match the contract
class ActivityType(IntEnum):
    LESSON_COMPLETION = 0
    DATASET_CONTRIBUTION = 1
    DAILY_PRACTICE = 2
    QUIZ_COMPLETION = 3
    ACHIEVEMENT_EARNED = 4

# Define roles from the contract
class Roles:
    # Don't use .hex() - the contract expects bytes32, not a hex string
    MINTER_ROLE = Web3.keccak(text="MINTER_ROLE")
    DEFAULT_ADMIN_ROLE = b"\x00" * 32  # 0x00...00

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
                    # Check if it's a rate limit error (HTTP 429)
                    is_rate_limit = False
                    if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                        is_rate_limit = e.response.status_code == 429
                    elif '429' in str(e):
                        is_rate_limit = True
                    
                    # Only retry on rate limit errors
                    if not is_rate_limit or retries >= max_retries:
                        raise
                    
                    # Log the retry
                    logger.warning(f"Rate limit hit, retrying in {current_backoff}s (retry {retries+1}/{max_retries})")
                    
                    # Wait before retrying
                    time.sleep(current_backoff)
                    retries += 1
                    current_backoff *= backoff_factor
        
        return cast(F, wrapper)
    return decorator


class XpRewardService:
    """Service for handling XP token rewards"""
    def __init__(self, blockchain: BlockchainService):
        self.w3 = blockchain.w3
        self.account = blockchain.account
        self.using_fallback_abi = False
        
        # Transaction tracking
        self.pending_transactions = defaultdict(list)  # address -> list of tx hashes
        self.transaction_details = {}  # tx_hash -> details
        
        # Use the ASLExperienceToken contract
        try:
            self.contract = blockchain.contracts.get("ASLExperienceToken")
            if not self.contract:
                # Fall back to using the ERC20_XP_CONTRACT_ADDRESS
                logger.info("ASLExperienceToken not found in contracts, using fallback ABI")
                self.using_fallback_abi = True
                self.contract = blockchain.w3.eth.contract(
                    address=Web3.to_checksum_address(settings.ERC20_XP_CONTRACT_ADDRESS),
                    abi=self._get_asl_experience_token_abi()
                )
        except Exception as e:
            # If there's any issue, create a contract instance directly
            logger.warning(f"Error loading contract from blockchain service: {str(e)}. Using fallback ABI.")
            self.using_fallback_abi = True
            self.contract = blockchain.w3.eth.contract(
                address=Web3.to_checksum_address(settings.ERC20_XP_CONTRACT_ADDRESS),
                abi=self._get_asl_experience_token_abi()
            )
            
        self.tx_manager = TransactionManager(blockchain.w3, blockchain.account)
        
        # Validate contract has expected functions
        self._validate_contract_functions()
    
    def _validate_contract_functions(self) -> None:
        """Validate that the contract has the expected functions"""
        required_functions = ["awardXP", "awardCustomXP", "updateRewardRate"]
        missing_functions = []
        
        for func_name in required_functions:
            if not hasattr(self.contract.functions, func_name):
                missing_functions.append(func_name)
        
        if missing_functions:
            logger.warning(f"Contract is missing expected functions: {', '.join(missing_functions)}")
            if self.using_fallback_abi:
                logger.error("Using fallback ABI but contract functions don't match expected interface")
    
    def _get_asl_experience_token_abi(self) -> list:
        """Load the ABI from the contract JSON file"""
        try:
            # Construct path to the contract JSON file
            contract_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))),
                'contracts',
                'ASLExperienceToken.json'
            )
            
            # Load the contract JSON
            with open(contract_path, 'r') as f:
                contract_json = json.load(f)
            
            # Extract the ABI
            if 'abi' in contract_json:
                logger.info("Successfully loaded ABI from contract JSON file")
                return contract_json['abi']
            else:
                logger.error("Contract JSON does not contain ABI")
                raise ValueError("Contract JSON does not contain ABI")
        except Exception as e:
            logger.error(f"Error loading contract ABI from file: {str(e)}")
            # Fallback to a minimal ABI with just the functions we need
            logger.warning("Using minimal fallback ABI")
            return [
                # hasRole function for role checking
                {
                    "inputs": [
                        {"name": "role", "type": "bytes32"},
                        {"name": "account", "type": "address"}
                    ],
                    "name": "hasRole",
                    "outputs": [{"name": "", "type": "bool"}],
                    "stateMutability": "view",
                    "type": "function"
                },
                # grantRole function for admin use
                {
                    "inputs": [
                        {"name": "role", "type": "bytes32"},
                        {"name": "account", "type": "address"}
                    ],
                    "name": "grantRole",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                # awardXP function
                {
                    "inputs": [
                        {"name": "to", "type": "address"},
                        {"name": "activityType", "type": "uint8"}
                    ],
                    "name": "awardXP",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                # awardCustomXP function
                {
                    "inputs": [
                        {"name": "to", "type": "address"},
                        {"name": "amount", "type": "uint256"},
                        {"name": "activityType", "type": "uint8"}
                    ],
                    "name": "awardCustomXP",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                # updateRewardRate function
                {
                    "inputs": [
                        {"name": "activityType", "type": "uint8"},
                        {"name": "newRate", "type": "uint256"}
                    ],
                    "name": "updateRewardRate",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]
    
    def check_minter_role(self) -> bool:
        """Check if the current account has the MINTER_ROLE"""
        try:
            has_role = self.contract.functions.hasRole(
                Roles.MINTER_ROLE,
                self.account.address
            ).call()
            
            if not has_role:
                logger.warning(f"Account {self.account.address} does not have MINTER_ROLE")
            
            return has_role
        except Exception as e:
            logger.error(f"Error checking MINTER_ROLE: {str(e)}")
            return False
    
    def grant_minter_role(self, address: str) -> dict:
        """Grant MINTER_ROLE to an address (must be called by admin)"""
        # Check if the current account has admin role
        try:
            has_admin = self.contract.functions.hasRole(
                Roles.DEFAULT_ADMIN_ROLE,
                self.account.address
            ).call()
            
            if not has_admin:
                logger.error(f"Account {self.account.address} does not have DEFAULT_ADMIN_ROLE")
                return {
                    'status': 'error',
                    'error': f"Account {self.account.address} does not have DEFAULT_ADMIN_ROLE",
                    'details': {
                        'function': 'grantRole',
                        'address': self.account.address,
                        'role': 'DEFAULT_ADMIN_ROLE'
                    }
                }
            
            # Convert address to checksum format
            checksummed_address = Web3.to_checksum_address(address)
            
            # Check if the address already has MINTER_ROLE
            has_role = self.contract.functions.hasRole(
                Roles.MINTER_ROLE,
                checksummed_address
            ).call()
            
            if has_role:
                logger.info(f"Address {checksummed_address} already has MINTER_ROLE")
                return {
                    'status': 'success',
                    'message': f"Address {checksummed_address} already has MINTER_ROLE"
                }
            
            # Prepare transaction to grant MINTER_ROLE
            tx_data = self.contract.functions.grantRole(
                Roles.MINTER_ROLE,
                checksummed_address
            ).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 100000,  # Gas limit
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Simulate transaction first
            self._simulate_transaction(tx_data)
            
            # Send the transaction
            return self._send_transaction(tx_data, {
                'function': 'grantRole',
                'role': 'MINTER_ROLE',
                'address': checksummed_address
            })
        except Exception as e:
            logger.error(f"Error granting MINTER_ROLE: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'details': {
                    'function': 'grantRole',
                    'role': 'MINTER_ROLE',
                    'address': address
                }
            }
    
    @retry_with_backoff(max_retries=3)
    def award_xp(self, address: str, activity_type: ActivityType) -> dict:
        """Award XP based on activity type using the contract's awardXP function"""
        # Ensure address is checksummed
        checksummed_address = Web3.to_checksum_address(address)
        
        # Check if account has MINTER_ROLE
        if not self.check_minter_role():
            return {
                'status': 'error',
                'error': f"Account {self.account.address} does not have MINTER_ROLE",
                'details': {
                    'function': 'awardXP',
                    'address': checksummed_address,
                    'activity_type': int(activity_type)
                }
            }
        
        # Build transaction
        tx_data = self.contract.functions.awardXP(
            checksummed_address,
            int(activity_type)  # Convert enum to int
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 1000000,  # High gas limit for Filecoin
            'gasPrice': self.w3.eth.gas_price
        })
        
        # Simulate transaction first
        self._simulate_transaction(tx_data)
        
        # Send transaction
        return self._send_transaction(tx_data, {
            'function': 'awardXP',
            'address': checksummed_address,
            'activity_type': int(activity_type),
        })
    
    @retry_with_backoff(max_retries=3)
    def award_custom_xp(self, address: str, amount: int, activity_type: ActivityType) -> dict:
        """Award a custom amount of XP using the contract's awardCustomXP function"""
        # Ensure address is checksummed
        checksummed_address = Web3.to_checksum_address(address)
        
        # Check if account has MINTER_ROLE
        if not self.check_minter_role():
            return {
                'status': 'error',
                'error': f"Account {self.account.address} does not have MINTER_ROLE",
                'details': {
                    'function': 'awardCustomXP',
                    'address': checksummed_address,
                    'amount': amount,
                    'activity_type': int(activity_type)
                }
            }
        
        # Build transaction
        tx_data = self.contract.functions.awardCustomXP(
            checksummed_address,
            amount,
            int(activity_type)  # Convert enum to int
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 1000000,  # High gas limit for Filecoin
            'gasPrice': self.w3.eth.gas_price
        })
        
        # Simulate transaction first
        self._simulate_transaction(tx_data)
        
        # Send transaction
        return self._send_transaction(tx_data, {
            'function': 'awardCustomXP',
            'address': checksummed_address,
            'amount': amount,
            'activity_type': int(activity_type)
        })
    
    @retry_with_backoff(max_retries=3)
    def update_reward_rate(self, activity_type: ActivityType, new_rate: int) -> dict:
        """Update the reward rate for an activity type"""
        # Check if account has admin role (typically needed for this function)
        try:
            has_admin = self.contract.functions.hasRole(
                Roles.DEFAULT_ADMIN_ROLE,
                self.account.address
            ).call()
            
            if not has_admin:
                logger.warning(f"Account {self.account.address} may not have permission to update reward rates")
        except Exception as e:
            logger.warning(f"Could not check admin role: {str(e)}")
        
        # Build transaction
        tx_data = self.contract.functions.updateRewardRate(
            int(activity_type),  # Convert enum to int
            new_rate
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 1000000,  # High gas limit for Filecoin
            'gasPrice': self.w3.eth.gas_price
        })
        
        # Simulate transaction first
        self._simulate_transaction(tx_data)
        
        # Send transaction
        return self._send_transaction(tx_data, {
            'function': 'updateRewardRate',
            'activity_type': int(activity_type),
            'new_rate': new_rate
        })
    
    # Keep the mint method for backward compatibility
    def mint(self, address: str, amount: int) -> dict:
        """Legacy method that uses award_custom_xp with DATASET_CONTRIBUTION activity type"""
        logger.warning("Using deprecated mint() method - this will call awardCustomXP instead")
        return self.award_custom_xp(address, amount, ActivityType.DATASET_CONTRIBUTION)
        
    def get_token_balance(self, address: str) -> int:
        """Get the current token balance for an address
        
        Args:
            address: Ethereum address to check balance for
            
        Returns:
            int: Current token balance
        """
        try:
            checksummed_address = Web3.to_checksum_address(address)
            balance = self.contract.functions.balanceOf(checksummed_address).call()
            logger.info(f"Token balance for {address}: {balance}")
            return balance
        except Exception as e:
            logger.error(f"Error getting token balance for {address}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get token balance: {str(e)}")
            
    def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        """Get the status of a transaction
        
        Args:
            tx_hash: Transaction hash to check
            
        Returns:
            dict: Transaction status and details
        """
        if tx_hash in self.transaction_details:
            return self.transaction_details[tx_hash]
            
        # If not in our cache, check the blockchain
        try:
            tx_receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            if tx_receipt:
                return {
                    "status": "confirmed" if tx_receipt.status == 1 else "failed",
                    "block_number": tx_receipt.blockNumber,
                    "gas_used": tx_receipt.gasUsed,
                    "timestamp": int(time.time())
                }
            else:
                # Transaction is pending
                return {"status": "pending", "timestamp": int(time.time())}
        except Exception as e:
            logger.error(f"Error getting transaction status for {tx_hash}: {str(e)}")
            return {"status": "unknown", "error": str(e), "timestamp": int(time.time())}
            
    def get_address_transactions(self, address: str) -> List[Dict[str, Any]]:
        """Get recent transactions for an address
        
        Args:
            address: Ethereum address to check transactions for
            
        Returns:
            list: List of recent transactions
        """
        tx_hashes = self.pending_transactions.get(address, [])
        transactions = []
        
        for tx_hash in tx_hashes:
            if tx_hash in self.transaction_details:
                transactions.append({
                    "tx_hash": tx_hash,
                    **self.transaction_details[tx_hash]
                })
                
        return transactions
    
    def _simulate_transaction(self, tx_data: TxParams) -> None:
        """Simulate a transaction to check for reverts before sending"""
        try:
            # Get function name for better error messages
            function_name = "unknown"
            
            # Handle data which could be bytes or string
            data = tx_data.get('data', b'')
            if isinstance(data, str):
                # Skip function name extraction for string data
                pass
            elif isinstance(data, bytes):
                try:
                    # Try to extract function name from bytes data
                    function_selector = data[:4].hex()
                    for fname in dir(self.contract.functions):
                        if not fname.startswith('__') and hasattr(self.contract.functions, fname):
                            if function_selector == self.contract.functions[fname].function_identifier.hex():
                                function_name = fname
                                break
                except Exception as e:
                    logger.debug(f"Could not extract function name: {e}")
            
            # Clone the transaction data for simulation
            call_data = dict(tx_data)
            # Remove gas-related keys for call() simulation
            for key in ['gas', 'gasPrice', 'maxFeePerGas', 'maxPriorityFeePerGas']:
                call_data.pop(key, None)
            
            logger.info(f"Simulating transaction for function: {function_name}")
            
            # Use call() to simulate the transaction
            # This will raise an exception if the transaction would revert
            self.w3.eth.call(call_data)
            
            logger.info(f"Transaction simulation successful for {function_name}")
        except ContractLogicError as e:
            # Extract revert reason if available
            revert_reason = str(e)
            if "reverted" in revert_reason:
                # Try to extract a cleaner error message
                if "execution reverted:" in revert_reason:
                    revert_reason = revert_reason.split("execution reverted:")[1].strip()
            
            logger.error(f"Transaction would revert: {revert_reason}")
            raise ValueError(f"Transaction would fail: {revert_reason}")
        except Exception as e:
            logger.error(f"Error simulating transaction: {str(e)}")
            raise ValueError(f"Transaction simulation failed: {str(e)}")
    
    @retry_with_backoff(max_retries=3)
    def _send_transaction(self, tx_data: TxParams, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Helper method to send a transaction and handle the response with retries"""
        try:
            # Add nonce management
            if 'nonce' not in tx_data:
                # Get the latest nonce for this account
                tx_data['nonce'] = self.w3.eth.get_transaction_count(self.account.address)
            
            start_time = time.time()
            tx_receipt = self.tx_manager.send_transaction(tx_data)
            end_time = time.time()
            
            # Calculate transaction duration
            duration_ms = int((end_time - start_time) * 1000)
            
            # Log transaction details
            tx_hash = tx_receipt.transactionHash.hex()
            logger.info(f"Transaction sent: {tx_hash}")
            
            # Track transaction for the address
            if details and 'address' in details:
                address = details['address']
                self.pending_transactions[address].append(tx_hash)
                # Store transaction details
                self.transaction_details[tx_hash] = {
                    "address": address,
                    "function": details.get('function', 'unknown'),
                    "timestamp": int(time.time()),
                    "status": "confirmed" if tx_receipt.status == 1 else "failed",
                    "block_number": tx_receipt.blockNumber,
                    "gas_used": tx_receipt.gasUsed
                }
                # Keep only the last 10 transactions per address
                if len(self.pending_transactions[address]) > 10:
                    old_tx = self.pending_transactions[address].pop(0)
                    if old_tx in self.transaction_details:
                        del self.transaction_details[old_tx]
            
            # Return success response
            result = {
                'tx_hash': tx_hash,
                'block': tx_receipt.blockNumber,
                'status': 'success',
                'gas_used': tx_receipt.gasUsed,
                'duration_ms': duration_ms
            }
            
            # Add transaction details if provided
            if details:
                result['details'] = details
                
            logger.info(f"Transaction successful: {result['tx_hash']}")
            return result
        except Exception as e:
            error_message = str(e)
            logger.error(f"Transaction failed: {error_message}")
            
            result = {
                'status': 'error',
                'error': error_message
            }
            
            # Add transaction details if provided
            if details:
                result['details'] = details
                
            return result
            
    def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        """Get the status of a transaction
        
        Args:
            tx_hash: Transaction hash to check
            
        Returns:
            dict: Transaction status and details
        """
        # Check if we have this transaction in our tracking system
        if tx_hash in self.transaction_details:
            return self.transaction_details[tx_hash]
            
        # If not in our tracking system, try to get it from the blockchain
        try:
            # Get transaction receipt
            tx_receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            if tx_receipt:
                # Transaction is confirmed
                return {
                    "status": "confirmed" if tx_receipt.status == 1 else "failed",
                    "block_number": tx_receipt.blockNumber,
                    "gas_used": tx_receipt.gasUsed,
                    "transaction_found": True
                }
            else:
                # Transaction is pending
                return {
                    "status": "pending",
                    "transaction_found": True
                }
        except Exception as e:
            # Transaction not found or other error
            return {
                "status": "unknown",
                "error": str(e),
                "transaction_found": False
            }
    
    def get_address_transactions(self, address: str) -> List[Dict[str, Any]]:
        """Get recent transactions for an address
        
        Args:
            address: Ethereum address to check transactions for
            
        Returns:
            list: List of recent transactions
        """
        # Normalize address
        address = Web3.to_checksum_address(address)
        
        # Get transaction hashes for this address
        tx_hashes = self.pending_transactions.get(address, [])
        
        # Get details for each transaction
        transactions = []
        for tx_hash in tx_hashes:
            # Get status from our tracking system or the blockchain
            status = self.get_transaction_status(tx_hash)
            transactions.append({
                "tx_hash": tx_hash,
                **status
            })
            
        return transactions


async def get_xp_reward_service(blockchain: BlockchainService = Depends(get_blockchain_service)) -> XpRewardService:
    """Dependency provider for XpRewardService"""
    service = XpRewardService(blockchain)
    return service