"""
XP Reward Service using the BaseContractService.
This module provides a service for handling XP token rewards.
"""
import logging
import json
import os
from enum import IntEnum
from typing import Any, Dict, Optional, List, Union, Tuple
import time

from web3 import Web3
from web3.types import TxParams, TxReceipt, Wei

from ...services.blockchain.core import BlockchainService, get_blockchain_service
from ...services.blockchain.base_contract import BaseContractService
from ...core.config import settings
from fastapi import Depends, HTTPException

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


class XpRewardServiceV2(BaseContractService):
    """Service for handling XP token rewards using the BaseContractService"""
    
    def __init__(self, blockchain: BlockchainService):
        """
        Initialize the XP reward service.
        
        Args:
            blockchain: BlockchainService instance
        """
        self.using_fallback_abi = False
        
        # Use the ASLExperienceToken contract
        try:
            contract = blockchain.contracts.get("ASLExperienceToken")
            if not contract:
                # Fall back to using the ERC20_XP_CONTRACT_ADDRESS
                logger.info("ASLExperienceToken not found in contracts, using fallback ABI")
                self.using_fallback_abi = True
                contract = blockchain.w3.eth.contract(
                    address=Web3.to_checksum_address(settings.ERC20_XP_CONTRACT_ADDRESS),
                    abi=self._get_asl_experience_token_abi()
                )
        except Exception as e:
            # If there's any issue, create a contract instance directly
            logger.warning(f"Error loading contract from blockchain service: {str(e)}. Using fallback ABI.")
            self.using_fallback_abi = True
            contract = blockchain.w3.eth.contract(
                address=Web3.to_checksum_address(settings.ERC20_XP_CONTRACT_ADDRESS),
                abi=self._get_asl_experience_token_abi()
            )
        
        # Initialize the base class
        super().__init__(blockchain.w3, blockchain.account, contract)
        
        # Validate contract has expected functions
        self._validate_contract_functions()
    
    def _validate_contract_functions(self) -> None:
        """Validate that the contract has the expected functions"""
        required_functions = ['awardXP', 'awardCustomXP', 'updateRewardRate', 'balanceOf', 'hasRole']
        missing_functions = [func for func in required_functions if not hasattr(self.contract.functions, func)]
        
        if missing_functions:
            logger.warning(f"Contract is missing expected functions: {', '.join(missing_functions)}")
            if self.using_fallback_abi:
                logger.warning("Using fallback ABI but still missing functions. Contract may not be compatible.")
            else:
                logger.warning("Consider using fallback ABI with _get_asl_experience_token_abi()")
    
    def _get_asl_experience_token_abi(self) -> List[Dict[str, Any]]:
        """Load the ABI from the contract JSON file"""
        try:
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'core','contracts', 's-contracts', 'abi', 'ASLExperienceToken.json')
            
            # Try each path until we find the file
            contract_json = None
            try:
                logger.info(f"Trying to load ABI from: {path}")
                with open(path, 'r') as f:
                    contract_json = json.load(f)
                    logger.info(f"Successfully loaded ABI from: {path}")
            except FileNotFoundError:
                logger.warning(f"Could not find ASLExperienceToken.json in {path}")
            except Exception as e:
                logger.warning(f"Error loading ABI from {path}: {str(e)}")
            
            if contract_json is None:
                raise FileNotFoundError("Could not find ASLExperienceToken.json in any of the expected locations")
                
            if isinstance(contract_json, dict) and 'abi' in contract_json:
                return contract_json['abi']
            return contract_json  # Assume the JSON itself is the ABI list
        except Exception as e:
            logger.warning(f"Could not load ABI from file: {str(e)}. Using minimal ABI.")
            # Return a minimal ABI with just the functions we need
            return [
                # awardXP function
                {
                    "inputs": [
                        {"internalType": "address", "name": "to", "type": "address"},
                        {"internalType": "uint256", "name": "activityType", "type": "uint256"}
                    ],
                    "name": "awardXP",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                # awardCustomXP function
                {
                    "inputs": [
                        {"internalType": "address", "name": "to", "type": "address"},
                        {"internalType": "uint256", "name": "amount", "type": "uint256"},
                        {"internalType": "uint256", "name": "activityType", "type": "uint256"}
                    ],
                    "name": "awardCustomXP",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                # updateRewardRate function
                {
                    "inputs": [
                        {"internalType": "uint256", "name": "activityType", "type": "uint256"},
                        {"internalType": "uint256", "name": "newRate", "type": "uint256"}
                    ],
                    "name": "updateRewardRate",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                # balanceOf function (ERC20 standard)
                {
                    "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                    "stateMutability": "view",
                    "type": "function"
                },
                # hasRole function (AccessControl)
                {
                    "inputs": [
                        {"internalType": "bytes32", "name": "role", "type": "bytes32"},
                        {"internalType": "address", "name": "account", "type": "address"}
                    ],
                    "name": "hasRole",
                    "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                    "stateMutability": "view",
                    "type": "function"
                },
                # grantRole function (AccessControl)
                {
                    "inputs": [
                        {"internalType": "bytes32", "name": "role", "type": "bytes32"},
                        {"internalType": "address", "name": "account", "type": "address"}
                    ],
                    "name": "grantRole",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]
    
    def check_minter_role(self) -> bool:
        """Check if the account has MINTER_ROLE"""
        try:
            logger.info(f"Checking minter role for account {self.account.address}")
            return self.contract.functions.hasRole(Roles.MINTER_ROLE, self.account.address).call()
        except Exception as e:
            logger.error(f"Error checking minter role: {str(e)}")
            return False
    
    def grant_minter_role(self, address: str) -> Dict[str, Any]:
        """Grant MINTER_ROLE to an address (must be called by admin)"""
        try:
            # Check if we have admin role
            has_admin = self.contract.functions.hasRole(Roles.DEFAULT_ADMIN_ROLE, self.account.address).call()
            if not has_admin:
                raise ValueError("Account does not have DEFAULT_ADMIN_ROLE required to grant roles")
            
            # Check if address already has the role
            has_role = self.contract.functions.hasRole(Roles.MINTER_ROLE, address).call()
            if has_role:
                return {
                    'status': 'success',
                    'message': f"Address {address} already has MINTER_ROLE"
                }
            
            # Estimate gas for the transaction
            gas_estimate = self.contract.functions.grantRole(
                Roles.MINTER_ROLE, 
                address
            ).estimate_gas({'from': self.account.address})
            
            # Add some buffer to the gas estimate
            gas_limit = int(gas_estimate * 1.2)
            
            # Get the current gas price
            gas_price = self.w3.eth.gas_price
            
            # Get the next nonce
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            # Build transaction using the contract functions interface
            func = self.contract.functions.grantRole(Roles.MINTER_ROLE, address)
            
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
            
            # Simulate the transaction to check for errors
            self._simulate_transaction(tx_data)
            
            # Send the transaction
            tx_details = {
                'function': 'grantRole',
                'role': 'MINTER_ROLE',
                'address': address
            }
            
            result = self._send_transaction(tx_data, tx_details)
            
            if result['status'] == 'success':
                return {
                    'status': 'success',
                    'message': f"Successfully granted MINTER_ROLE to {address}",
                    'tx_hash': result['tx_hash']
                }
            else:
                return {
                    'status': 'error',
                    'message': f"Failed to grant MINTER_ROLE: {result.get('error', 'Unknown error')}",
                    'tx_hash': result.get('tx_hash')
                }
        except Exception as e:
            logger.error(f"Error granting minter role: {str(e)}")
            return {
                'status': 'error',
                'message': f"Error granting minter role: {str(e)}",
                'tx_hash': None
            }
    
    def award_xp(self, address: str, activity_type: ActivityType) -> Dict[str, Any]:
        """Award XP based on activity type using the contract's awardXP function"""
        try:
            logger.info(f"Now awarding XP to {address} for activity type {activity_type}")
            # Validate address
            if not Web3.is_address(address):
                raise ValueError(f"Invalid Ethereum address: {address}")
            
            # Convert to checksum address
            address = Web3.to_checksum_address(address)
            
            # Check if we have minter role
            try:
                has_minter_role = self.check_minter_role()
                if not has_minter_role:
                    logger.warning(f"Account {self.account.address} does not have MINTER_ROLE required to award XP")
                    return {
                        'status': 'error',
                        'error': "Account does not have MINTER_ROLE required to award XP",
                        'error_category': 'permission_error',
                        'tx_hash': None,
                        'timestamp': int(time.time())
                    }
            except Exception as e:
                logger.error(f"Error checking minter role: {str(e)}")
                # Continue anyway, the transaction will fail if we don't have permission
            
            # Estimate gas for the transaction
            logger.info(f"Estimating gas for awardXP transaction")
            func = self.contract.functions.awardXP(
                address, 
                int(activity_type)
            )
            gas_estimate = func.estimate_gas({'from': self.account.address})
            
            # Add some buffer to the gas estimate
            gas_limit = int(gas_estimate * 1.2)
            logger.info(f"Estimated gas: {gas_estimate}, using gas limit: {gas_limit}")
            
            # Get the current gas price
            gas_price = self.w3.eth.gas_price
            logger.info(f"Current gas price: {Web3.from_wei(gas_price, 'gwei')} gwei")
            
            # Get the next nonce
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            # Build transaction using the contract functions interface directly
            func = self.contract.functions.awardXP(address, int(activity_type))
            
            # Get EIP-1559 fee parameters
            max_fee, priority_fee, base_fee, use_eip1559 = self._get_eip1559_fees()
            logger.info(f"EIP-1559 fees calculated: base_fee={Web3.from_wei(base_fee, 'gwei')} gwei, " +
                       f"priority_fee={Web3.from_wei(priority_fee, 'gwei')} gwei, " +
                       f"max_fee={Web3.from_wei(max_fee, 'gwei')} gwei")
            
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
            
            # Simulate the transaction to check for errors
            self._simulate_transaction(tx_data)
            
            # Get the current balance before the transaction
            try:
                balance_before = self.contract.functions.balanceOf(address).call()
            except Exception as balance_error:
                logger.warning(f"Could not get balance before transaction: {str(balance_error)}")
                balance_before = None
            
            # Send the transaction
            tx_details = {
                'function': 'awardXP',
                'activity_type': int(activity_type),
                'activity_name': activity_type.name,
                'address': address,
                'balance_before': balance_before
            }
            
            result = self._send_transaction(tx_data, tx_details)
            
            # Try to get the new balance after the transaction
            try:
                if result['status'] == 'success':
                    balance_after = self.contract.functions.balanceOf(address).call()
                    result['balance_after'] = balance_after
                    result['xp_awarded'] = balance_after - balance_before if balance_before is not None else None
            except Exception as balance_error:
                logger.warning(f"Could not get balance after transaction: {str(balance_error)}")
            
            return result
        except Exception as e:
            logger.error(f"Error awarding XP: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'error_category': 'unexpected_error',
                'tx_hash': None,
                'timestamp': int(time.time()),
                'details': {
                    'function': 'awardXP',
                    'activity_type': int(activity_type) if isinstance(activity_type, ActivityType) else activity_type,
                    'address': address
                }
            }
    
    def award_custom_xp(self, address: str, amount: int, activity_type: ActivityType) -> Dict[str, Any]:
        """Award a custom amount of XP using the contract's awardCustomXP function"""
        try:
            # Validate address
            if not Web3.is_address(address):
                raise ValueError(f"Invalid Ethereum address: {address}")
            
            # Convert to checksum address
            address = Web3.to_checksum_address(address)
            
            # Check if we have minter role
            if not self.check_minter_role():
                raise ValueError("Account does not have MINTER_ROLE required to award XP")
            
            # Validate amount
            if amount <= 0:
                raise ValueError(f"Amount must be positive, got {amount}")
            
            # Estimate gas for the transaction
            gas_estimate = self.contract.functions.awardCustomXP(
                address, 
                amount,
                int(activity_type)
            ).estimate_gas({'from': self.account.address})
            
            # Add some buffer to the gas estimate
            gas_limit = int(gas_estimate * 1.2)
            
            # Get the current gas price
            gas_price = self.w3.eth.gas_price
            
            # Get the next nonce
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            # Build transaction using the contract functions interface directly
            func = self.contract.functions.awardCustomXP(address, amount, int(activity_type))
            
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
            
            # Simulate the transaction to check for errors
            self._simulate_transaction(tx_data)
            
            # Get the current balance before the transaction
            try:
                balance_before = self.contract.functions.balanceOf(address).call()
            except Exception as balance_error:
                logger.warning(f"Could not get balance before transaction: {str(balance_error)}")
                balance_before = None
            
            # Send the transaction
            tx_details = {
                'function': 'awardCustomXP',
                'amount': amount,
                'activity_type': int(activity_type),
                'activity_name': activity_type.name,
                'address': address,
                'balance_before': balance_before
            }
            
            result = self._send_transaction(tx_data, tx_details)
            
            # Try to get the new balance after the transaction
            try:
                if result['status'] == 'success':
                    balance_after = self.contract.functions.balanceOf(address).call()
                    result['balance_after'] = balance_after
                    result['xp_awarded'] = balance_after - balance_before if balance_before is not None else None
            except Exception as balance_error:
                logger.warning(f"Could not get balance after transaction: {str(balance_error)}")
            
            return result
        except Exception as e:
            logger.error(f"Error awarding custom XP: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'error_category': 'unexpected_error',
                'tx_hash': None,
                'timestamp': int(time.time()),
                'details': {
                    'function': 'awardCustomXP',
                    'amount': amount,
                    'activity_type': int(activity_type) if isinstance(activity_type, ActivityType) else activity_type,
                    'address': address
                }
            }
    
    def update_reward_rate(self, activity_type: ActivityType, new_rate: int) -> Dict[str, Any]:
        """Update the reward rate for an activity type"""
        try:
            # Check if we have admin role
            has_admin = self.contract.functions.hasRole(Roles.DEFAULT_ADMIN_ROLE, self.account.address).call()
            if not has_admin:
                raise ValueError("Account does not have DEFAULT_ADMIN_ROLE required to update reward rates")
            
            # Validate new rate
            if new_rate <= 0:
                raise ValueError(f"New rate must be positive, got {new_rate}")
            
            # Estimate gas for the transaction
            try:
                gas_estimate = self.contract.functions.updateRewardRate(
                    int(activity_type), 
                    new_rate
                ).estimate_gas({'from': self.account.address})
                
                # Add some buffer to the gas estimate
                gas_limit = int(gas_estimate * 1.2)
            except Exception as e:
                logger.warning(f"Failed to estimate gas: {str(e)}. Using default gas limit.")
                gas_limit = 300000  # Lower default gas limit than before
            
            # Get the current gas price
            gas_price = self.w3.eth.gas_price
            
            # Get the next nonce
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
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
            
            # Simulate the transaction to check for errors
            self._simulate_transaction(tx_data)
            
            # Send the transaction
            tx_details = {
                'function': 'updateRewardRate',
                'activity_type': int(activity_type),
                'activity_name': activity_type.name,
                'new_rate': new_rate,
                'address': self.account.address  # Using our own address for tracking
            }
            
            result = self._send_transaction(tx_data, tx_details)
            
            return result
        except Exception as e:
            logger.error(f"Error updating reward rate: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'error_category': 'unexpected_error',
                'tx_hash': None,
                'timestamp': int(time.time()),
                'details': {
                    'function': 'updateRewardRate',
                    'activity_type': int(activity_type) if isinstance(activity_type, ActivityType) else activity_type,
                    'new_rate': new_rate
                }
            }
    
    def mint(self, address: str, amount: int) -> Dict[str, Any]:
        """Legacy method that uses award_custom_xp with DATASET_CONTRIBUTION activity type"""
        return self.award_custom_xp(address, amount, ActivityType.DATASET_CONTRIBUTION)
    
    def get_token_balance(self, address: str) -> int:
        """
        Get the current token balance for an address
        
        Args:
            address: Ethereum address to check balance for
            
        Returns:
            int: Current token balance
        """
        try:
            # Validate address
            if not Web3.is_address(address):
                raise ValueError(f"Invalid Ethereum address: {address}")
            
            # Convert to checksum address
            address = Web3.to_checksum_address(address)
            
            # Call the balanceOf function
            return self.contract.functions.balanceOf(address).call()
        except Exception as e:
            logger.error(f"Error getting token balance: {str(e)}")
            raise


# Dependency provider for XpRewardServiceV2
def get_xp_reward_service_v2(blockchain: BlockchainService = Depends(get_blockchain_service)):
    return XpRewardServiceV2(blockchain)
