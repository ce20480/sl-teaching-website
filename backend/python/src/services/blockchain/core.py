# services/blockchain.py
from web3 import Web3
from eth_account import Account
from ...core.contracts.registry import ContractRegistry
from ...core.config import settings
from fastapi import Depends

# Singleton instance
_blockchain_service = None

def get_blockchain_service():
    """Dependency provider for BlockchainService"""
    global _blockchain_service
    if _blockchain_service is None:
        _blockchain_service = BlockchainService()
    return _blockchain_service

class BlockchainService:
    """Service for interacting with blockchain contracts"""
    def __init__(self):
        self.registry = ContractRegistry()
        self.w3 = Web3(Web3.HTTPProvider(settings.FILECOIN_TESTNET_RPC_URL))
        self.account = Account.from_key(settings.BLOCKCHAIN_PRIVATE_KEY)
        
        # Only load contracts if they exist
        self.contracts = {}
        try:
            self.contracts["erc20_xp"] = self._load_contract("erc20_xp")
        except (FileNotFoundError, ValueError):
            pass

    def _load_contract(self, name: str):
        """Load a contract by name, with fallback to standard ABIs"""
        try:
            # Try to load from registry first
            return self.w3.eth.contract(
                address=self.registry.get_address(name),
                abi=self.registry.get_abi(name)
            )
        except (FileNotFoundError, ValueError) as e:
            # If contract not in registry, use standard ABI
            if name == "erc20_xp":
                return self.w3.eth.contract(
                    address=settings.ERC20_XP_CONTRACT_ADDRESS,
                    abi=self._get_standard_erc20_abi()
                )
            raise e
            
    def _get_standard_erc20_abi(self):
        """Return a minimal ERC20 ABI with mint function"""
        return [
            {
                "constant": False,
                "inputs": [
                    {"name": "to", "type": "address"},
                    {"name": "value", "type": "uint256"}
                ],
                "name": "mint",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [{"name": "owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            }
        ]