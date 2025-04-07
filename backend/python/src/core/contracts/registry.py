# core/contracts/registry.py
from pathlib import Path
import json
from ..config import settings

class ContractRegistry:
    def __init__(self):
        self.abi_path = Path(__file__).parent.parent / "contracts/abis"
        
    def get_abi(self, contract_name: str) -> list:
        """Load ABI from local artifacts with validation"""
        path = self.abi_path / f"{contract_name}.json"
        with open(path) as f:
            artifact = json.load(f)
            
        if not isinstance(artifact.get('abi'), list):
            raise ValueError(f"Invalid ABI format in {contract_name}")
            
        return artifact['abi']

    def get_address(self, contract_name: str) -> str:
        """Get address from environment variables"""
        return getattr(settings, f"TFIL_{contract_name.upper()}_CONTRACT_ADDRESS", "")