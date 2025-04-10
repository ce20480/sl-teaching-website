"""
Achievement Reward Service using the BaseContractService.
This module provides a service for handling Achievement token rewards.
"""
import logging
import time
from enum import IntEnum
from typing import Any, Dict, List

from web3 import Web3
from eth_account import Account

from ..blockchain.base_contract import BaseContractService
from ...core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Define AchievementType enum to match the contract
class AchievementType(IntEnum):
    BEGINNER = 0
    INTERMEDIATE = 1
    ADVANCED = 2
    EXPERT = 3
    MASTER = 4


class AchievementRewardService(BaseContractService):
    """Service for handling Achievement token rewards using the BaseContractService"""
    
    def __init__(self):
        """
        Initialize the Achievement reward service.
        
        Args:
            blockchain: BlockchainService instance
        """
        w3 = Web3(Web3.HTTPProvider(settings.FILECOIN_TESTNET_RPC_URL))
        account = Account.from_key(settings.BLOCKCHAIN_PRIVATE_KEY)

        # Use the AchievementToken contract
        try:
            abi = settings.achievement_contract_abi
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(settings.TFIL_ACHIEVEMENT_CONTRACT_ADDRESS),
                abi=abi
            )
        except Exception as e:
            # If there's any issue, create a contract instance directly
            logger.warning(f"Error loading contract from blockchain service: {str(e)}. Using fallback ABI.")
        
        # Initialize the base class
        super().__init__(w3, account, contract)
        
        # Achievement thresholds for backward compatibility
        self.achievement_thresholds = {
            'BEGINNER': 100,
            'INTERMEDIATE': 500,
            'ADVANCED': 750,
            'EXPERT': 1000,
            'MASTER': 2000
        }
        
        # Validate contract has expected functions
        self._validate_contract_functions()
    
    def _validate_contract_functions(self) -> None:
        """Validate that the contract has the expected functions"""
        required_functions = ['mintAchievement', 'updateMetadata', 'getUserAchievements', 'getAchievement']
        missing_functions = [func for func in required_functions if not hasattr(self.contract.functions, func)]
        
        if missing_functions:
            logger.warning(f"Contract is missing expected functions: {', '.join(missing_functions)}")
            logger.warning("Contract may not be compatible with this service.")
    
    def mint_achievement(self, address: str, achievement_type: AchievementType, ipfs_hash: str, description: str) -> Dict[str, Any]:
        """
        Mint an achievement NFT for a user
        
        Args:
            address: Recipient address
            achievement_type: Type of achievement (enum value)
            ipfs_hash: IPFS hash for the achievement metadata
            description: Description of the achievement
            
        Returns:
            Dict with transaction status and details
        """
        try:
            # Validate address
            if not Web3.is_address(address):
                raise ValueError(f"Invalid Ethereum address: {address}")
            
            # Convert to checksum address
            address = Web3.to_checksum_address(address)
            
            # Validate achievement type
            if not isinstance(achievement_type, AchievementType) and not isinstance(achievement_type, int):
                raise ValueError(f"Invalid achievement type: {achievement_type}")
            
            # Convert to int if it's an enum
            achievement_type_int = int(achievement_type)
            
            # Estimate gas for the transaction
            gas_estimate = self.contract.functions.mintAchievement(
                address,
                achievement_type_int,
                ipfs_hash,
                description
            ).estimate_gas({'from': self.account.address})
            
            # Add some buffer to the gas estimate
            gas_limit = int(gas_estimate * 1.2)
            
            # Get the next nonce
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            # Build transaction using the contract functions interface
            func = self.contract.functions.mintAchievement(
                address,
                achievement_type_int,
                ipfs_hash,
                description
            )
            
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
                gas_price = self.w3.eth.gas_price
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
                'function': 'mintAchievement',
                'achievement_type': achievement_type_int,
                'achievement_name': achievement_type.name if isinstance(achievement_type, AchievementType) else f"Type_{achievement_type_int}",
                'ipfs_hash': ipfs_hash,
                'description': description,
                'address': address
            }
            
            result = self._send_transaction(tx_data, tx_details)
            
            # Try to get the token ID from the transaction receipt if successful
            if result['status'] == 'success' and 'tx_receipt' in result:
                try:
                    # Extract token ID from logs
                    receipt = result['tx_receipt']
                    # Look for Transfer event logs (standard ERC-721 event)
                    for log in receipt.get('logs', []):
                        # ERC-721 Transfer event has 4 topics: event signature, from, to, tokenId
                        if len(log.get('topics', [])) == 4:
                            # The last topic is the token ID
                            token_id = int(log['topics'][3].hex(), 16)
                            result['token_id'] = token_id
                            break
                except Exception as e:
                    logger.warning(f"Could not extract token ID from receipt: {str(e)}")
            
            return result
        except Exception as e:
            logger.error(f"Error minting achievement: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'error_category': 'unexpected_error',
                'tx_hash': None,
                'timestamp': int(time.time()),
                'details': {
                    'function': 'mintAchievement',
                    'achievement_type': int(achievement_type) if isinstance(achievement_type, (AchievementType, int)) else achievement_type,
                    'ipfs_hash': ipfs_hash,
                    'description': description,
                    'address': address
                }
            }
    
    def update_metadata(self, token_id: int, new_ipfs_hash: str) -> Dict[str, Any]:
        """
        Update the metadata for an existing achievement NFT
        
        Args:
            token_id: Token ID to update
            new_ipfs_hash: New IPFS hash for the achievement metadata
            
        Returns:
            Dict with transaction status and details
        """
        try:
            # Validate token ID
            if not isinstance(token_id, int) or token_id < 0:
                raise ValueError(f"Invalid token ID: {token_id}")
            
            # Estimate gas for the transaction
            gas_estimate = self.contract.functions.updateMetadata(
                token_id,
                new_ipfs_hash
            ).estimate_gas({'from': self.account.address})
            
            # Add some buffer to the gas estimate
            gas_limit = int(gas_estimate * 1.2)
            
            # Get the next nonce
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            # Build transaction using the contract functions interface
            func = self.contract.functions.updateMetadata(token_id, new_ipfs_hash)
            
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
                gas_price = self.w3.eth.gas_price
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
                'function': 'updateMetadata',
                'token_id': token_id,
                'new_ipfs_hash': new_ipfs_hash,
                'address': self.account.address  # Using our own address for tracking
            }
            
            result = self._send_transaction(tx_data, tx_details)
            
            return result
        except Exception as e:
            logger.error(f"Error updating metadata: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'error_category': 'unexpected_error',
                'tx_hash': None,
                'timestamp': int(time.time()),
                'details': {
                    'function': 'updateMetadata',
                    'token_id': token_id,
                    'new_ipfs_hash': new_ipfs_hash
                }
            }
    
    def get_user_achievements(self, address: str) -> List[int]:
        """
        Get all achievement token IDs owned by a user
        
        Args:
            address: User address to check
            
        Returns:
            List of token IDs owned by the user
        """
        try:
            # Validate address
            if not Web3.is_address(address):
                raise ValueError(f"Invalid Ethereum address: {address}")
            
            # Convert to checksum address
            address = Web3.to_checksum_address(address)
            
            # Call the getUserAchievements function
            return self.contract.functions.getUserAchievements(address).call()
        except Exception as e:
            logger.error(f"Error getting user achievements: {str(e)}")
            return []
    
    def get_achievement_details(self, token_id: int) -> Dict[str, Any]:
        """
        Get details for a specific achievement token
        
        Args:
            token_id: Token ID to get details for
            
        Returns:
            Dict with achievement details
        """
        try:
            # Validate token ID
            if not isinstance(token_id, int) or token_id < 0:
                raise ValueError(f"Invalid token ID: {token_id}")
            
            # Call the getAchievement function
            achievement = self.contract.functions.getAchievement(token_id).call()
            
            # Format the result
            return {
                'token_id': token_id,
                'achievement_type': achievement[0],
                'achievement_name': AchievementType(achievement[0]).name if achievement[0] < len(AchievementType) else f"Type_{achievement[0]}",
                'ipfs_hash': achievement[1],
                'timestamp': achievement[2],
                'description': achievement[3]
            }
        except Exception as e:
            logger.error(f"Error getting achievement details: {str(e)}")
            return {
                'token_id': token_id,
                'error': str(e)
            }
    
    def get_user_achievement_details(self, address: str) -> List[Dict[str, Any]]:
        """
        Get details for all achievements owned by a user
        
        Args:
            address: User address to check
            
        Returns:
            List of dicts with achievement details
        """
        try:
            # Get all token IDs owned by the user
            token_ids = self.get_user_achievements(address)
            
            # Get details for each token
            achievements = []
            for token_id in token_ids:
                achievement = self.get_achievement_details(token_id)
                achievements.append(achievement)
            
            return achievements
        except Exception as e:
            logger.error(f"Error getting user achievement details: {str(e)}")
            return []
    
    def award_achievement_by_xp(self, address: str, xp_amount: int, ipfs_hash: str = "") -> Dict[str, Any]:
        """
        Award an achievement based on XP amount
        
        Args:
            address: User address
            xp_amount: XP amount to determine achievement level
            ipfs_hash: IPFS hash for achievement metadata (optional)
            
        Returns:
            Dict with transaction status and details
        """
        try:
            # Determine achievement type based on XP amount
            achievement_type = None
            for level in sorted(AchievementType, key=lambda x: self.achievement_thresholds[x.name]):
                if xp_amount >= self.achievement_thresholds[level.name]:
                    achievement_type = level
                else:
                    break
            
            if achievement_type is None:
                return {
                    'status': 'error',
                    'error': f"XP amount {xp_amount} does not qualify for any achievement level",
                    'error_category': 'validation_error',
                    'tx_hash': None
                }
            
            # Generate description
            description = f"Earned {achievement_type.name} achievement with {xp_amount} XP"
            
            # Mint the achievement
            return self.mint_achievement(address, achievement_type, ipfs_hash, description)
        except Exception as e:
            logger.error(f"Error awarding achievement by XP: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'error_category': 'unexpected_error',
                'tx_hash': None,
                'timestamp': int(time.time()),
                'details': {
                    'function': 'award_achievement_by_xp',
                    'xp_amount': xp_amount,
                    'address': address
                }
            }


# Dependency provider for AchievementRewardService
def get_achievement_reward_service():
    return AchievementRewardService()
