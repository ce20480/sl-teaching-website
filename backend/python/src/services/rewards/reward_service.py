from typing import Dict, Any
from web3 import Web3
from eth_account import Account
from eth_typing import Address
import json
import os
from ..evaluation.evaluator import EvaluationResult, EvaluationStatus

class RewardService:
    """Service to handle achievement token rewards for contributions"""
    
    def __init__(self):
        # Initialize Web3 connection (using environment variables)
        self.w3 = Web3(Web3.HTTPProvider(os.getenv('WEB3_PROVIDER_URL')))
        self.contract_address = os.getenv('ACHIEVEMENT_CONTRACT_ADDRESS')
        self.private_key = os.getenv('REWARD_SERVICE_PRIVATE_KEY')
        
        # Load contract ABI
        with open('contracts/AchievementToken.json') as f:
            contract_json = json.load(f)
            self.contract_abi = contract_json['abi']
        
        # Initialize contract
        self.contract = self.w3.eth.contract(
            address=self.contract_address,
            abi=self.contract_abi
        )
        
        # Initialize account
        self.account = Account.from_key(self.private_key)
    
    async def process_evaluation_result(
        self,
        user_address: str,
        evaluation_result: EvaluationResult,
        contribution_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process evaluation results and award tokens if appropriate
        """
        if evaluation_result.status != EvaluationStatus.APPROVED:
            return {
                "success": False,
                "message": "Contribution not approved for reward"
            }
        
        try:
            # Determine achievement type based on contribution quality
            achievement_type = self._determine_achievement_type(
                evaluation_result.score,
                contribution_metadata
            )
            
            # Prepare transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            # Prepare contract call
            tx = self.contract.functions.mintAchievement(
                user_address,
                achievement_type,
                contribution_metadata.get('ipfs_hash', ''),
                f"Contribution Achievement - Quality Score: {evaluation_result.score}"
            ).build_transaction({
                'nonce': nonce,
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(
                tx,
                private_key=self.private_key
            )
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                "success": True,
                "transaction_hash": receipt['transactionHash'].hex(),
                "achievement_type": achievement_type,
                "score": evaluation_result.score
            }
            
        except Exception as e:
            print(f"Error minting achievement token: {e}")
            return {
                "success": False,
                "message": f"Failed to mint achievement token: {str(e)}"
            }
    
    def _determine_achievement_type(
        self,
        score: float,
        metadata: Dict[str, Any]
    ) -> int:
        """
        Determine the achievement type based on contribution quality
        Returns achievement type enum index (0-4)
        """
        # For now, use a simple threshold-based system
        # TODO: Implement more sophisticated achievement type determination
        if score >= 0.95:
            return 4  # MASTER
        elif score >= 0.90:
            return 3  # EXPERT
        elif score >= 0.85:
            return 2  # ADVANCED
        elif score >= 0.80:
            return 1  # INTERMEDIATE
        else:
            return 0  # BEGINNER 