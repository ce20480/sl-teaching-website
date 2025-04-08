# services/reward/xp_reward.py
import logging
import time
import functools
import asyncio
import json
import os
from enum import IntEnum
from typing import Any, Callable, Dict, Optional, TypeVar, cast, List, Union, Tuple

from web3 import Web3
from web3.exceptions import ContractLogicError
from web3.types import TxParams, TxReceipt, Wei

from ...services.blockchain.core import BlockchainService, get_blockchain_service
from ...services.blockchain.nonce_manager import NonceManager
from ...services.blockchain.rate_limiter import RateLimiter
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
        
        # Initialize nonce manager and rate limiter
        self.nonce_manager = NonceManager(self.w3, self.account.address)
        self.rate_limiter = RateLimiter(max_requests=5, refill_rate=1.0, refill_interval=1.0)
        
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
        """Check if the account has MINTER_ROLE"""
        try:
            return self.contract.functions.hasRole(
                Roles.MINTER_ROLE,
                self.account.address
            ).call()
        except Exception as e:
            logger.error(f"Error checking MINTER_ROLE: {str(e)}")
            return False
            
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
        
        # Log the award attempt
        logger.info(f"Attempting to award XP to {checksummed_address} for activity {activity_type}")
        
        # Check if account has MINTER_ROLE
        if not self.check_minter_role():
            error_msg = f"Account {self.account.address} does not have MINTER_ROLE"
            logger.error(error_msg)
            return {
                'status': 'error',
                'error': error_msg,
                'details': {
                    'function': 'awardXP',
                    'address': checksummed_address,
                    'activity_type': int(activity_type)
                }
            }
        
        # Check account balance before proceeding
        account_balance = self.w3.eth.get_balance(self.account.address)
        logger.info(f"Account balance before transaction: {Web3.from_wei(account_balance, 'ether')} ETH")
        
        # Get current gas price
        gas_price = self.w3.eth.gas_price
        logger.info(f"Current gas price: {Web3.from_wei(gas_price, 'gwei')} gwei")
        
        # Get next nonce from nonce manager
        nonce = self.nonce_manager.get_next_nonce()
        logger.info(f"Using nonce: {nonce}")
        
        # First estimate gas to get a more accurate gas limit
        try:
            # Use the contract functions interface directly for gas estimation
            func = self.contract.functions.awardXP(checksummed_address, int(activity_type))
            estimated_gas = func.estimate_gas({'from': self.account.address})
            # Add a buffer to the estimated gas (20%)
            gas_limit = int(estimated_gas * 1.2)
            logger.info(f"Estimated gas: {estimated_gas}, using gas limit: {gas_limit}")
        except Exception as e:
            logger.warning(f"Failed to estimate gas: {str(e)}. Using default gas limit.")
            gas_limit = 300000  # Lower default gas limit than before
        
        # Build transaction using the contract functions interface directly
        func = self.contract.functions.awardXP(checksummed_address, int(activity_type))
        
        # Get EIP-1559 fee parameters
        max_fee, priority_fee, base_fee, use_eip1559 = self._get_eip1559_fees()
        
        if use_eip1559:
            # For EIP-1559 transactions
            tx_data = func.build_transaction({
                'chainId': self.w3.eth.chain_id,
                'from': self.account.address,
                'gas': gas_limit,
                'maxFeePerGas': max_fee,
                'maxPriorityFeePerGas': priority_fee,
                'nonce': nonce
            })
            logger.info(f"Using EIP-1559 transaction with maxFeePerGas: {Web3.from_wei(max_fee, 'gwei')} gwei, " +
                       f"maxPriorityFeePerGas: {Web3.from_wei(priority_fee, 'gwei')} gwei")
        else:
            # For legacy transactions
            tx_data = func.build_transaction({
                'chainId': self.w3.eth.chain_id,
                'from': self.account.address,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': nonce
            })
        
        try:
            # Simulate transaction first
            logger.info("Simulating transaction before sending")
            self._simulate_transaction(tx_data)
            logger.info("Simulation successful, proceeding with transaction")
            
            # Send transaction
            result = self._send_transaction(tx_data, {
                'function': 'awardXP',
                'address': checksummed_address,
                'activity_type': int(activity_type),
            })
            
            # Log the result
            if result['status'] == 'success':
                logger.info(f"Successfully awarded XP to {checksummed_address} with tx hash {result.get('tx_hash')}")
            else:
                logger.error(f"Failed to award XP: {result.get('error')}")
                
            return result
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Exception during XP award: {error_msg}")
            
            # Create a detailed error response
            return {
                'status': 'error',
                'error': error_msg,
                'details': {
                    'function': 'awardXP',
                    'address': checksummed_address,
                    'activity_type': int(activity_type),
                    'account_balance': str(Web3.from_wei(account_balance, 'ether')),
                    'gas_price': str(Web3.from_wei(gas_price, 'gwei')),
                    'nonce': nonce
                }
            }
    
    @retry_with_backoff(max_retries=3)
    def award_custom_xp(self, address: str, amount: int, activity_type: ActivityType) -> dict:
        """Award a custom amount of XP using the contract's awardCustomXP function"""
        # Ensure address is checksummed
        checksummed_address = Web3.to_checksum_address(address)
        
        # Log the award attempt
        logger.info(f"Attempting to award {amount} custom XP to {checksummed_address} for activity {activity_type}")
        
        # Check if account has MINTER_ROLE
        if not self.check_minter_role():
            error_msg = f"Account {self.account.address} does not have MINTER_ROLE"
            logger.error(error_msg)
            return {
                'status': 'error',
                'error': error_msg,
                'details': {
                    'function': 'awardCustomXP',
                    'address': checksummed_address,
                    'amount': amount,
                    'activity_type': int(activity_type)
                }
            }
        
        # Check account balance before proceeding
        account_balance = self.w3.eth.get_balance(self.account.address)
        logger.info(f"Account balance before transaction: {Web3.from_wei(account_balance, 'ether')} ETH")
        
        # Get current gas price
        gas_price = self.w3.eth.gas_price
        logger.info(f"Current gas price: {Web3.from_wei(gas_price, 'gwei')} gwei")
        
        # Get next nonce from nonce manager
        nonce = self.nonce_manager.get_next_nonce()
        logger.info(f"Using nonce: {nonce}")
        
        # First estimate gas to get a more accurate gas limit
        try:
            # Use the contract functions interface directly for gas estimation
            func = self.contract.functions.awardCustomXP(checksummed_address, amount, int(activity_type))
            estimated_gas = func.estimate_gas({'from': self.account.address})
            # Add a buffer to the estimated gas (20%)
            gas_limit = int(estimated_gas * 1.2)
            logger.info(f"Estimated gas: {estimated_gas}, using gas limit: {gas_limit}")
        except Exception as e:
            logger.warning(f"Failed to estimate gas: {str(e)}. Using default gas limit.")
            gas_limit = 300000  # Lower default gas limit than before
        
        # Build transaction using the contract functions interface directly
        func = self.contract.functions.awardCustomXP(checksummed_address, amount, int(activity_type))
        
        # Get EIP-1559 fee parameters
        max_fee, priority_fee, base_fee, use_eip1559 = self._get_eip1559_fees()
        
        if use_eip1559:
            # For EIP-1559 transactions
            tx_data = func.build_transaction({
                'chainId': self.w3.eth.chain_id,
                'from': self.account.address,
                'gas': gas_limit,
                'maxFeePerGas': max_fee,
                'maxPriorityFeePerGas': priority_fee,
                'nonce': nonce
            })
            logger.info(f"Using EIP-1559 transaction with maxFeePerGas: {Web3.from_wei(max_fee, 'gwei')} gwei, " +
                       f"maxPriorityFeePerGas: {Web3.from_wei(priority_fee, 'gwei')} gwei")
        else:
            # For legacy transactions
            tx_data = func.build_transaction({
                'chainId': self.w3.eth.chain_id,
                'from': self.account.address,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': nonce
            })
        
        try:
            # Simulate transaction first
            logger.info(f"Simulating transaction before sending (custom amount: {amount})")
            self._simulate_transaction(tx_data)
            logger.info("Simulation successful, proceeding with transaction")
            
            # Send transaction
            result = self._send_transaction(tx_data, {
                'function': 'awardCustomXP',
                'address': checksummed_address,
                'amount': amount,
                'activity_type': int(activity_type)
            })
            
            # Log the result
            if result['status'] == 'success':
                logger.info(f"Successfully awarded {amount} custom XP to {checksummed_address} with tx hash {result.get('tx_hash')}")
            else:
                logger.error(f"Failed to award custom XP: {result.get('error')}")
                
            return result
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Exception during custom XP award: {error_msg}")
            
            # Create a detailed error response
            return {
                'status': 'error',
                'error': error_msg,
                'details': {
                    'function': 'awardCustomXP',
                    'address': checksummed_address,
                    'amount': amount,
                    'activity_type': int(activity_type),
                    'account_balance': str(Web3.from_wei(account_balance, 'ether')),
                    'gas_price': str(Web3.from_wei(gas_price, 'gwei')),
                    'nonce': nonce
                }
            }
    
    @retry_with_backoff(max_retries=3)
    def update_reward_rate(self, activity_type: ActivityType, new_rate: int) -> dict:
        """Update the reward rate for an activity type"""
        # Log the update attempt
        logger.info(f"Attempting to update reward rate for activity type {activity_type} to {new_rate}")
        
        # Check if account has admin role (typically needed for this function)
        try:
            has_admin = self.contract.functions.hasRole(
                Roles.DEFAULT_ADMIN_ROLE,
                self.account.address
            ).call()
            
            if not has_admin:
                error_msg = f"Account {self.account.address} does not have DEFAULT_ADMIN_ROLE required to update reward rates"
                logger.error(error_msg)
                return {
                    'status': 'error',
                    'error': error_msg,
                    'details': {
                        'function': 'updateRewardRate',
                        'activity_type': int(activity_type),
                        'new_rate': new_rate
                    }
                }
        except Exception as e:
            logger.warning(f"Could not check admin role: {str(e)}")
        
        # Check account balance before proceeding
        account_balance = self.w3.eth.get_balance(self.account.address)
        logger.info(f"Account balance before transaction: {Web3.from_wei(account_balance, 'ether')} ETH")
        
        # Get current gas price
        gas_price = self.w3.eth.gas_price
        logger.info(f"Current gas price: {Web3.from_wei(gas_price, 'gwei')} gwei")
        
        # Get next nonce from nonce manager
        nonce = self.nonce_manager.get_next_nonce()
        logger.info(f"Using nonce: {nonce}")
        
        # First estimate gas to get a more accurate gas limit
        try:
            # Use the contract's functions interface to build the transaction
            func = self.contract.functions.updateRewardRate(int(activity_type), new_rate)
            estimated_gas = func.estimate_gas({'from': self.account.address})
            # Add a buffer to the estimated gas (20%)
            gas_limit = int(estimated_gas * 1.2)
            logger.info(f"Estimated gas: {estimated_gas}, using gas limit: {gas_limit}")
        except Exception as e:
            logger.warning(f"Failed to estimate gas: {str(e)}. Using default gas limit.")
            gas_limit = 300000  # Lower default gas limit than before
        
        # Build transaction using the contract functions interface directly
        func = self.contract.functions.updateRewardRate(int(activity_type), new_rate)
        
        # Get EIP-1559 fee parameters
        max_fee, priority_fee, base_fee, use_eip1559 = self._get_eip1559_fees()
        
        if use_eip1559:
            # For EIP-1559 transactions
            tx_data = func.build_transaction({
                'chainId': self.w3.eth.chain_id,
                'from': self.account.address,
                'gas': gas_limit,
                'maxFeePerGas': max_fee,
                'maxPriorityFeePerGas': priority_fee,
                'nonce': nonce
            })
            logger.info(f"Using EIP-1559 transaction with maxFeePerGas: {Web3.from_wei(max_fee, 'gwei')} gwei, " +
                       f"maxPriorityFeePerGas: {Web3.from_wei(priority_fee, 'gwei')} gwei")
        else:
            # For legacy transactions
            tx_data = func.build_transaction({
                'chainId': self.w3.eth.chain_id,
                'from': self.account.address,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': nonce
            })
        
        try:
            # Simulate transaction first
            logger.info(f"Simulating updateRewardRate transaction before sending")
            self._simulate_transaction(tx_data)
            logger.info("Simulation successful, proceeding with transaction")
        
            # Send transaction
            result = self._send_transaction(tx_data, {
                'function': 'updateRewardRate',
                'activity_type': int(activity_type),
                'new_rate': new_rate
            })
            
            # Log the result
            if result['status'] == 'success':
                logger.info(f"Successfully updated reward rate for activity type {activity_type} to {new_rate} with tx hash {result.get('tx_hash')}")
            else:
                logger.error(f"Failed to update reward rate: {result.get('error')}")
                
            return result
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Exception during reward rate update: {error_msg}")
            
            # Create a detailed error response
            return {
                'status': 'error',
                'error': error_msg,
                'details': {
                    'function': 'updateRewardRate',
                    'activity_type': int(activity_type),
                    'new_rate': new_rate,
                    'account_balance': str(Web3.from_wei(account_balance, 'ether')),
                    'gas_price': str(Web3.from_wei(gas_price, 'gwei')),
                    'nonce': nonce
                }
            }
    
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
        """Simulate a transaction to check if it would succeed"""
        try:
            # Create a copy of the transaction data for simulation
            call_data = tx_data.copy()
            
            # Get function name for logging
            function_name = "unknown"
            if 'data' in tx_data and tx_data['data']:
                # Try to decode the function selector
                try:
                    function_selector = tx_data['data'][:10]  # First 4 bytes (8 hex chars + '0x')
                    for name in dir(self.contract.functions):
                        if name.startswith('__'):
                            continue
                        func = getattr(self.contract.functions, name)
                        if hasattr(func, 'selector') and func.selector == function_selector:
                            function_name = name
                            break
                except Exception as decode_error:
                    logger.debug(f"Could not decode function selector: {str(decode_error)}")
            
            # Log transaction details for debugging
            logger.info(f"Transaction details for simulation:\n" + 
                       f"From: {tx_data.get('from', 'Not specified')}\n" +
                       f"To: {tx_data.get('to', 'Not specified')}\n" +
                       f"Value: {tx_data.get('value', 0)}\n" +
                       f"Gas: {tx_data.get('gas', 'Not specified')}\n" +
                       f"Function: {function_name}")
            
            # Remove gas-related fields for simulation
            for key in ['gas', 'gasPrice', 'maxFeePerGas', 'maxPriorityFeePerGas']:
                call_data.pop(key, None)
            
            logger.info(f"Simulating transaction for function: {function_name}")
            
            # Use call() to simulate the transaction
            # This will raise an exception if the transaction would revert
            result = self.w3.eth.call(call_data)
            
            # Log the simulation result
            try:
                # Try to decode the result if it's not empty
                logger.debug(f"Simulation result: {result.hex()}")
            except Exception:
                logger.debug(f"Simulation successful with result: {result}")
                
            # Additional checks for common issues
            # Check if the account has enough balance for gas
            account_balance = self.w3.eth.get_balance(tx_data['from'])
            estimated_gas_cost = tx_data.get('gas', 21000) * (
                tx_data.get('gasPrice', 0) or 
                self.w3.eth.gas_price
            )
            
            if account_balance < estimated_gas_cost:
                logger.warning(f"Warning: Account may have insufficient balance for gas.\n" +
                             f"Balance: {Web3.from_wei(account_balance, 'ether')} ETH\n" +
                             f"Estimated cost: {Web3.from_wei(estimated_gas_cost, 'ether')} ETH")
            
            logger.info(f"Transaction simulation successful for {function_name}")
            
            # Check if the account has enough balance for gas
            account_balance = self.w3.eth.get_balance(tx_data['from'])
            estimated_gas_cost = tx_data.get('gas', 21000) * tx_data.get('gasPrice', self.w3.eth.gas_price)
            
            if account_balance < estimated_gas_cost:
                logger.error(f"Insufficient balance for gas. Have: {Web3.from_wei(account_balance, 'ether')} ETH, " +
                             f"Need approximately: {Web3.from_wei(estimated_gas_cost, 'ether')} ETH")
                raise ValueError(f"Insufficient balance for gas. Account balance: {Web3.from_wei(account_balance, 'ether')} ETH")
            
        except ContractLogicError as e:
            # Extract revert reason if available
            revert_reason = str(e)
            if "reverted" in revert_reason:
                # Try to extract a cleaner error message
                if "execution reverted:" in revert_reason:
                    revert_reason = revert_reason.split("execution reverted:")[1].strip()
            
            logger.error(f"Transaction would revert: {revert_reason}")
            
            # Log more detailed information about the transaction
            logger.error(f"Transaction details for failed simulation:")
            logger.error(f"  To: {tx_data.get('to', 'Not specified')}")
            logger.error(f"  From: {tx_data.get('from', self.account.address)}")
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
            
            # Check account balance before sending
            account_balance = self.w3.eth.get_balance(self.account.address)
            estimated_gas_cost = tx_data.get('gas', 21000) * tx_data.get('gasPrice', self.w3.eth.gas_price)
            logger.info(f"Account balance: {Web3.from_wei(account_balance, 'ether')} ETH")
            logger.info(f"Estimated gas cost: {Web3.from_wei(estimated_gas_cost, 'ether')} ETH")
            
            if account_balance < estimated_gas_cost:
                error_msg = f"Insufficient balance for gas. Have: {Web3.from_wei(account_balance, 'ether')} ETH, " + \
                           f"Need approximately: {Web3.from_wei(estimated_gas_cost, 'ether')} ETH"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
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
                                
                            # Try to simulate the transaction to get the revert reason
                            try:
                                # Call the contract with the same parameters to see the revert reason
                                if details and 'function' in details:
                                    if details['function'] == 'awardXP' and 'address' in details and 'activity_type' in details:
                                        try:
                                            call_result = self.contract.functions.awardXP(
                                                details['address'], details['activity_type']).call({'from': self.account.address})
                                            logger.info(f"Contract call simulation result: {call_result}")
                                        except Exception as call_err:
                                            # This should actually fail with the same error as the transaction
                                            error_message = str(call_err)
                                            if 'revert' in error_message.lower():
                                                logger.error(f"Contract reverted with reason: {error_message}")
                                            else:
                                                logger.error(f"Contract call simulation failed: {error_message}")
                                    elif details['function'] == 'awardCustomXP' and 'address' in details and 'amount' in details and 'activity_type' in details:
                                        try:
                                            call_result = self.contract.functions.awardCustomXP(
                                                details['address'], details['amount'], details['activity_type']).call({'from': self.account.address})
                                            logger.info(f"Contract call simulation result: {call_result}")
                                        except Exception as call_err:
                                            error_message = str(call_err)
                                            if 'revert' in error_message.lower():
                                                logger.error(f"Contract reverted with reason: {error_message}")
                                            else:
                                                logger.error(f"Contract call simulation failed: {error_message}")
                            except Exception as sim_error:
                                logger.error(f"Could not simulate transaction: {str(sim_error)}")
                    except Exception as debug_error:
                        logger.error(f"Could not get additional debug info: {str(debug_error)}")
            except Exception as receipt_error:
                end_time = time.time()
                duration_ms = int((end_time - start_time) * 1000)
                status = "failed"
                error_str = str(receipt_error)
                logger.error(f"Error waiting for transaction receipt: {error_str}")
                
                # Check if this is a rate limit error
                if "429" in error_str or "Too Many Requests" in error_str:
                    logger.warning("Rate limit exceeded when waiting for receipt. Transaction may still be pending.")
                    
                    # Set transaction details to pending with rate limit error
                    if tx_hash in self.transaction_details:
                        self.transaction_details[tx_hash].update({
                            "status": "pending",
                            "error": "Rate limit exceeded when checking status. Try again later.",
                            "error_category": "rate_limited",
                            "duration_ms": duration_ms
                        })
                    
                    return {
                        'status': 'pending',
                        'message': 'Transaction sent but status check was rate limited. Try checking status later.',
                        'error_category': 'rate_limited',
                        'tx_hash': tx_hash,
                        'timestamp': int(time.time()),
                        'duration_ms': duration_ms,
                        'details': details
                    }
                
                # Set default values since we couldn't get the receipt
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
                if len(self.pending_transactions[address]) > 10:
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
                            # Try to decode each log
                            decoded = self.contract.events.XPAwarded().process_log(log)
                            if decoded:
                                decoded_logs.append({
                                    'event': decoded.event,
                                    'args': {k: str(v) for k, v in decoded.args.items()}
                                })
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
            elif "replacement transaction underpriced" in error_message.lower():
                error_category = "underpriced_replacement"
                current_gas_price = Web3.from_wei(self.w3.eth.gas_price, 'gwei')
                tx_gas_price = Web3.from_wei(tx_data.get('gasPrice', 0), 'gwei')
                logger.error(f"Replacement transaction needs higher gas price. Current network gas price: {current_gas_price} gwei, Transaction gas price: {tx_gas_price} gwei")
            elif "execution reverted" in error_message.lower():
                error_category = "contract_revert"
                logger.error(f"Smart contract execution reverted: {error_message}")
            elif "timeout" in error_message.lower():
                error_category = "network_timeout"
                logger.error(f"Network timeout when sending transaction. Check network connectivity and RPC endpoint status.")
            elif "connection" in error_message.lower():
                error_category = "connection_error"
                logger.error(f"Connection error when sending transaction. Check network connectivity: {error_message}")
            else:
                logger.error(f"Uncategorized transaction error: {error_message}")
            
            result = {
                'status': 'error',
                'error': error_message,
                'error_category': error_category,
                'tx_hash': tx_hash,
                'timestamp': int(time.time())
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
            # First check if transaction exists
            try:
                # Get the transaction itself
                tx = self.w3.eth.get_transaction(tx_hash)
                logger.info(f"Found transaction {tx_hash} with nonce {tx.get('nonce')}")
            except Exception as e:
                logger.warning(f"Transaction {tx_hash} not found: {str(e)}")
                return {
                    "status": "not_found",
                    "error": f"Transaction not found: {str(e)}",
                    "transaction_found": False,
                    "timestamp": int(time.time())
                }
            
            # Get transaction receipt
            tx_receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            if tx_receipt:
                # Get more detailed information about the transaction
                status = "confirmed" if tx_receipt.status == 1 else "failed"
                result = {
                    "status": status,
                    "block_number": tx_receipt.blockNumber,
                    "gas_used": tx_receipt.gasUsed,
                    "transaction_found": True,
                    "timestamp": int(time.time())
                }
                
                # If transaction failed, try to get more information
                if status == "failed":
                    try:
                        # Check if we used all gas - likely an error in execution
                        if tx_receipt.gasUsed >= (tx.get('gas', 0) * 0.95):  # Used more than 95% of gas limit
                            result["error_details"] = "Transaction used almost all gas. This usually indicates a runtime error."
                            logger.error(f"Transaction {tx_hash} failed using {tx_receipt.gasUsed}/{tx.get('gas', 0)} gas")
                    except Exception as debug_error:
                        logger.error(f"Could not get additional debug info: {str(debug_error)}")
                
                return result
            else:
                # Transaction is pending
                block_number = self.w3.eth.block_number
                pending_block_count = block_number - tx.get('blockNumber', 0)
                result = {
                    "status": "pending",
                    "transaction_found": True,
                    "nonce": tx.get('nonce'),
                    "gas": tx.get('gas'),
                    "gas_price": tx.get('gasPrice'),
                    "timestamp": int(time.time()),
                    "pending_for_blocks": pending_block_count,
                    "current_block": block_number
                }
                return result
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error getting transaction status: {error_msg}")
        
            # Categorize common errors
            if "not found" in error_msg.lower():
                status = "not_found"
            else:
                status = "error"
            
            return {
                "status": status,
                "error": error_msg,
                "transaction_found": False,
                "timestamp": int(time.time())
            }

    def get_transactions(self, address: str) -> List[Dict[str, Any]]:
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