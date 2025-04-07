# from typing import Dict, Any
# from web3 import Web3
# from eth_account import Account
# import json
# from pathlib import Path
# from ..core.config import settings
# from ..services.evaluator import EvaluationResult
# from ..services.blockchain import BlockchainService

# class RewardService:
#     """Service to handle achievement token and XP rewards for contributions"""
    
#     def __init__(self):
#         # Initialize Web3 connection (using environment variables)
#         self.w3 = Web3(Web3.HTTPProvider(settings.WEB3_PROVIDER_URL))
#         self.achievement_contract_address = settings.TFIL_ACHIEVEMENT_CONTRACT_ADDRESS
#         self.xp_contract_address = settings.TFIL_XP_TOKEN_CONTRACT_ADDRESS
#         self.private_key = settings.WEB3_PRIVATE_KEY
#         self.chainId = settings.CHAIN_ID
#         path = Path(__file__).parents[4]
        
#         # Load contract ABIs
#         with open(path / 'contracts' / 'AchievementToken.json') as f:
#             contract_json = json.load(f)
#             self.achievement_contract_abi = contract_json['abi']
        
#         with open(path / 'contracts' / 'ASLExperienceToken.json') as f:
#             contract_json = json.load(f)
#             self.xp_contract_abi = contract_json['abi']
        
#         # Initialize contracts
#         self.achievement_contract = self.w3.eth.contract(
#             address=self.achievement_contract_address,
#             abi=self.achievement_contract_abi
#         )
        
#         self.xp_contract = self.w3.eth.contract(
#             address=self.xp_contract_address,
#             abi=self.xp_contract_abi
#         )
        
#         # Initialize account
#         self.account = Account.from_key(self.private_key)
    
#     async def process_evaluation_result(
#         self,
#         user_address: str,
#         evaluation_result: EvaluationResult,
#         contribution_metadata: Dict[str, Any]
#     ) -> Dict[str, Any]:
#         """
#         Process evaluation results and award tokens if appropriate
#         """
#         if evaluation_result.status != EvaluationStatus.APPROVED:
#             return {
#                 "success": False,
#                 "message": "Contribution not approved for reward"
#             }
        
#         try:
#             # Determine achievement type based on contribution quality
#             achievement_type = self._determine_achievement_type(
#                 evaluation_result.score,
#                 contribution_metadata
#             )
            
#             # Prepare transaction
#             nonce = self.w3.eth.get_transaction_count(self.account.address)
            
#             # Prepare contract call
#             tx = self.achievement_contract.functions.mintAchievement(
#                 user_address,
#                 achievement_type,
#                 contribution_metadata.get('ipfs_hash', ''),
#                 f"Contribution Achievement - Quality Score: {evaluation_result.score}"
#             ).build_transaction({
#                 'nonce': nonce,
#                 'gas': 500000,
#                 'gasPrice': self.w3.eth.gas_price,
#                 'chainId': self.chainId
#             })
            
#             # Sign and send transaction
#             signed_tx = self.w3.eth.account.sign_transaction(
#                 tx,
#                 private_key=self.private_key
#             )
#             tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
#             # Wait for transaction receipt
#             receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
#             return {
#                 "success": True,
#                 "transaction_hash": receipt['transactionHash'].hex(),
#                 "achievement_type": achievement_type,
#                 "score": evaluation_result.score
#             }
            
#         except Exception as e:
#             print(f"Error minting achievement token: {e}")
#             return {
#                 "success": False,
#                 "message": f"Failed to mint achievement token: {str(e)}"
#             }
    
#     def _determine_achievement_type(
#         self,
#         score: float,
#         metadata: Dict[str, Any]
#     ) -> int:
#         """
#         Determine the achievement type based on contribution quality
#         Returns achievement type enum index (0-4)
#         """
#         # For now, use a simple threshold-based system
#         # TODO: Implement more sophisticated achievement type determination
#         if score >= 0.95:
#             return 4  # MASTER
#         elif score >= 0.90:
#             return 3  # EXPERT
#         elif score >= 0.85:
#             return 2  # ADVANCED
#         elif score >= 0.80:
#             return 1  # INTERMEDIATE
#         else:
#             return 0  # BEGINNER 
    
#     # async def award_xp_for_contribution(self, user_address: str, quality_score: float) -> Dict[str, Any]:
#     #     """
#     #     Award XP tokens to a user for their contribution
        
#     #     Args:
#     #         user_address: User's wallet address
#     #         quality_score: Quality score of the contribution (0-1)
            
#     #     Returns:
#     #         Dict with transaction details
#     #     """
#     #     try:
#     #         # Get nonce for the transaction
#     #         nonce = self.w3.eth.get_transaction_count(self.account.address)
            
#     #         # Determine activity type (1 = DATASET_CONTRIBUTION)
#     #         activity_type = 1
            
#     #         # Build the transaction
#     #         tx = self.xp_contract.functions.awardXP(
#     #             user_address,
#     #             activity_type
#     #         ).build_transaction({
#     #             'chainId': self.chainId,
#     #             'gas': 200000,
#     #             'gasPrice': self.w3.eth.gas_price,
#     #             'nonce': nonce,
#     #         })
            
#     #         # Sign and send the transaction
#     #         signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
#     #         tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
#     #         # Wait for transaction receipt
#     #         receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
#     #         return {
#     #             "success": True,
#     #             "transaction_hash": receipt.transactionHash.hex(),
#     #             "activity_type": "Dataset Contribution",
#     #             "xp_awarded": True
#     #         }
            
#     #     except Exception as e:
#     #         print(f"Error awarding XP: {str(e)}")
#     #         return {
#     #             "success": False,
#     #             "error": str(e)
#     #         }
#     async def award_xp_for_contribution(self, user_address: str, quality_score: float) -> Dict[str, Any]:
#         try:
#             nonce = self.w3.eth.get_transaction_count(self.account.address)
#             xp_amount = int(quality_score * 100)
            
#             tx = self.xp_contract.functions.mint(
#                 user_address,
#             xp_amount
#             ).build_transaction({
#                 'chainId': self.chainId,
#                 'gas': 200000,
#                 'gasPrice': self.w3.eth.gas_price,
#                 'nonce': nonce,
#             })

#             # Fix 1: Use proper private key format
#             signed_tx = self.account.sign_transaction(tx)  # Use the initialized Account instance
#             tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
#             receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
#             return {
#                 "success": True,
#                 "tx_hash": tx_hash.hex(),
#                 "gas_used": receipt.gasUsed
#             }
        
#         except Exception as e:
#             return {"success": False, "error": str(e)}

#     async def get_xp_balance(self, address: str) -> float:
#         """
#         Get the XP balance for a user
        
#         Args:
#             address: User's wallet address
            
#         Returns:
#             Current XP balance
#         """
#         try:
#             # Call the XP token contract to get balance
#             balance = await self.xp_contract.functions.balanceOf(address).call()
#             # Convert from wei (assuming 18 decimals)
#             return balance / 10**18
#         except Exception as e:
#             print(f"Error getting XP balance: {str(e)}")
#             # Return 0 as fallback
#             return 0

#     async def get_user_achievements(self, address: str) -> list:
#         """
#         Get the achievements for a user
        
#         Args:
#             address: User's wallet address
            
#         Returns:
#             List of achievement data
#         """
#         try:
#             # Call the Achievement contract to get tokens
#             token_count = await self.achievement_contract.functions.balanceOf(address).call()
            
#             achievements = []
#             # For each token, get its metadata
#             for i in range(token_count):
#                 token_id = await self.achievement_contract.functions.tokenOfOwnerByIndex(address, i).call()
#                 token_uri = await self.achievement_contract.functions.tokenURI(token_id).call()
                
#                 # You may want to fetch and parse the actual metadata from IPFS
#                 # For now, just return the URI
#                 achievements.append({
#                     "token_id": token_id,
#                     "token_uri": token_uri
#                 })
                
#             return achievements
#         except Exception as e:
#             print(f"Error getting achievements: {str(e)}")
#             return [] 