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
                # Try to load ABI from the contract JSON file first
                try:
                    abi = self._load_abi_from_file("ASLExperienceToken.json")
                    return self.w3.eth.contract(
                        address=settings.ERC20_XP_CONTRACT_ADDRESS,
                        abi=abi
                    )
                except Exception as abi_error:
                    # Fall back to minimal ABI if file loading fails
                    import logging
                    logging.getLogger(__name__).warning(f"Failed to load ABI from file: {str(abi_error)}. Using minimal ABI.")
                    return self.w3.eth.contract(
                        address=settings.ERC20_XP_CONTRACT_ADDRESS,
                        abi=self._get_standard_erc20_abi()
                    )
            raise e
            
    def _load_abi_from_file(self, filename: str):
        """Load ABI from a contract JSON file"""
        import os
        import json
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Try multiple possible locations for the contract file
        possible_paths = [
            # Root project directory
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), 'contracts', filename),
            # One level up from backend
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))), 'contracts', filename),
            # Inside backend directory
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), 'contracts', filename),
            # Current directory
            os.path.join(os.path.dirname(__file__), filename)
        ]
        
        # Try each path until we find the file
        contract_json = None
        for path in possible_paths:
            try:
                logger.info(f"Trying to load ABI from: {path}")
                with open(path, 'r') as f:
                    contract_json = json.load(f)
                    logger.info(f"Successfully loaded ABI from: {path}")
                    break
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.warning(f"Error loading ABI from {path}: {str(e)}")
                continue
        
        if contract_json is None:
            raise FileNotFoundError(f"Could not find {filename} in any of the expected locations")
            
        # Extract the ABI
        if isinstance(contract_json, dict) and 'abi' in contract_json:
            return contract_json['abi']
        return contract_json  # Assume the JSON itself is the ABI list
            
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