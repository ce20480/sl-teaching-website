# services/reward/achievement_reward.py
from enum import IntEnum
from web3 import Web3
from ...services.blockchain.core import BlockchainService, get_blockchain_service
from ...services.blockchain.transactions import TransactionManager
from ...core.config import settings
from fastapi import Depends

# Define AchievementType enum to match the contract
class AchievementType(IntEnum):
    BEGINNER = 0
    INTERMEDIATE = 1
    ADVANCED = 2
    EXPERT = 3
    MASTER = 4

class AchievementRewardService:
    """Service for handling Achievement token rewards"""
    def __init__(self, blockchain: BlockchainService):
        # Use the AchievementToken contract
        try:
            self.contract = blockchain.contracts.get("AchievementToken")
            if not self.contract:
                # Fall back to using the ACHIEVEMENT_CONTRACT_ADDRESS
                self.contract = blockchain.w3.eth.contract(
                    address=Web3.to_checksum_address(settings.TFIL_ACHIEVEMENT_CONTRACT_ADDRESS),
                    abi=self._get_achievement_token_abi()
                )
        except Exception as e:
            # If there's any issue, create a contract instance directly
            self.contract = blockchain.w3.eth.contract(
                address=Web3.to_checksum_address(settings.TFIL_ACHIEVEMENT_CONTRACT_ADDRESS),
                abi=self._get_achievement_token_abi()
            )
            
        self.tx_manager = TransactionManager(blockchain.w3, blockchain.account)
        
        # Achievement thresholds for backward compatibility
        self.achievement_thresholds = {
            'BEGINNER': 100,
            'INTERMEDIATE': 500,
            'ADVANCED': 750,
            'EXPERT': 1000,
            'MASTER': 2000
        }
    
    def _get_achievement_token_abi(self):
        """Return the ABI for AchievementToken with the functions we need"""
        return [
            # mintAchievement function
            {
                "inputs": [
                    {"name": "to", "type": "address"},
                    {"name": "achievementType", "type": "uint8"},
                    {"name": "ipfsHash", "type": "string"},
                    {"name": "description", "type": "string"}
                ],
                "name": "mintAchievement",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            # updateMetadata function
            {
                "inputs": [
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "newIpfsHash", "type": "string"}
                ],
                "name": "updateMetadata",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            # getUserAchievements function
            {
                "inputs": [
                    {"name": "user", "type": "address"}
                ],
                "name": "getUserAchievements",
                "outputs": [{"name": "", "type": "uint256[]"}],
                "stateMutability": "view",
                "type": "function"
            },
            # getAchievement function
            {
                "inputs": [
                    {"name": "tokenId", "type": "uint256"}
                ],
                "name": "getAchievement",
                "outputs": [{
                    "components": [
                        {"name": "achievementType", "type": "uint8"},
                        {"name": "ipfsHash", "type": "string"},
                        {"name": "timestamp", "type": "uint256"},
                        {"name": "description", "type": "string"}
                    ],
                    "name": "", 
                    "type": "tuple"
                }],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    async def mint_achievement(self, address: str, achievement_type: AchievementType, 
                              ipfs_hash: str, description: str) -> dict:
        """Mint a new achievement token"""
        # Ensure address is checksummed
        checksummed_address = Web3.to_checksum_address(address)
        
        # Build transaction
        tx_data = self.contract.functions.mintAchievement(
            checksummed_address,
            int(achievement_type),  # Convert enum to int
            ipfs_hash,
            description
        ).build_transaction({
            'from': self.tx_manager.account.address,
            'gas': 1000000  # High gas limit for Filecoin
        })
        
        return await self._send_transaction(tx_data)
    
    async def update_metadata(self, token_id: int, new_ipfs_hash: str) -> dict:
        """Update the IPFS hash for a token's metadata"""
        # Build transaction
        tx_data = self.contract.functions.updateMetadata(
            token_id,
            new_ipfs_hash
        ).build_transaction({
            'from': self.tx_manager.account.address,
            'gas': 1000000  # High gas limit for Filecoin
        })
        
        return await self._send_transaction(tx_data)
    
    async def get_user_achievements(self, address: str) -> list:
        """Get all achievements for a user"""
        checksummed_address = Web3.to_checksum_address(address)
        return await self.contract.functions.getUserAchievements(checksummed_address).call()
    
    async def get_achievement(self, token_id: int) -> dict:
        """Get achievement details for a specific token"""
        achievement = await self.contract.functions.getAchievement(token_id).call()
        return {
            'achievement_type': achievement[0],
            'ipfs_hash': achievement[1],
            'timestamp': achievement[2],
            'description': achievement[3]
        }
    
    # Legacy method for backward compatibility
    async def award_achievement(self, user_address: str, total_xp: int) -> dict:
        """Award achievement NFT based on cumulative XP"""
        try:
            achievement_type = self._determine_achievement_level(total_xp)
            ipfs_hash = settings.TFIL_ACHIEVEMENT_HASH  # Use the hash from settings
            description = f"{achievement_type.name} Level Achievement"
            
            return await self.mint_achievement(
                user_address, 
                achievement_type, 
                ipfs_hash, 
                description
            )
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _determine_achievement_level(self, total_xp: int) -> AchievementType:
        """Determine achievement level based on XP"""
        if total_xp >= self.achievement_thresholds['MASTER']:
            return AchievementType.MASTER
        elif total_xp >= self.achievement_thresholds['EXPERT']:
            return AchievementType.EXPERT
        elif total_xp >= self.achievement_thresholds['ADVANCED']:
            return AchievementType.ADVANCED
        elif total_xp >= self.achievement_thresholds['INTERMEDIATE']:
            return AchievementType.INTERMEDIATE
        else:
            return AchievementType.BEGINNER
    
    async def _send_transaction(self, tx_data: dict) -> dict:
        """Helper method to send a transaction and handle the response"""
        try:
            receipt = await self.tx_manager.send_transaction(tx_data)
            return {
                'tx_hash': receipt.transactionHash.hex(),
                'block': receipt.blockNumber,
                'status': 'success'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }


def get_achievement_reward_service(blockchain: BlockchainService = Depends(get_blockchain_service)) -> AchievementRewardService:
    """Dependency provider for AchievementRewardService"""
    return AchievementRewardService(blockchain)