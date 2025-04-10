from functools import lru_cache
from pydantic_settings import BaseSettings
from pathlib import Path
from pydantic import Field
import json
import logging

# Load .env file once at startup, but because I am using pydantic it does the loading all for me
# from dotenv import load_dotenv
# load_dotenv(Path(__file__).parents[2] / ".env")

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Keep existing fields
    WEB3_PRIVATE_KEY: str = Field(default="")
    NODE_ADDRESS: str = "connect.akave.ai:5500"
    DEFAULT_BUCKET: str = "asl-training-data"
    MODEL_PATH: str = Field(default="./models/asl_model.pkl")
    WEB3_PROVIDER_URL: str = Field(default="https://api.calibration.node.glif.io/rpc/v1")
    
    # Add missing fields that exist in .env
    REWARD_SERVICE_PRIVATE_KEY: str = Field(default="")
    DEPLOYER_ADDRESS: str = Field(default="")
    TFIL_ACHIEVEMENT_CONTRACT_ADDRESS: str = Field(default="")
    TFIL_XP_TOKEN_CONTRACT_ADDRESS: str = Field(default="")
    TFIL_ACHIEVEMENT_HASH: str = Field(default="")
    CHAIN_ID: int = Field(default=314159)

    # Add blockchain configuration settings
    FILECOIN_TESTNET_RPC_URL: str = Field(..., env="FILECOIN_TESTNET_RPC_URL")
    BLOCKCHAIN_PRIVATE_KEY: str = Field(..., env="BLOCKCHAIN_PRIVATE_KEY")
    ERC20_XP_CONTRACT_ADDRESS: str = Field(default="0xB65A3b71b5856a70Fd55E5926d4a22931Bd048D5", env="ERC20_XP_CONTRACT_ADDRESS")

    class Config:
        env_file = Path(__file__).parents[2] / ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True
        # extra = 'allow'  # Temporarily allow extra fields during transition

    # Add ABI loading logic
    @property
    def xp_contract_abi(self) -> dict:
        """Load XP contract ABI from file"""
        abi_path = Path(__file__).parent / "contracts" / "s-contracts" / "abi" / "ASLExperienceToken.json"
        logger.info(f"Loading XP contract ABI from file: {abi_path}")
        return self._load_abi(abi_path)
    
    @property
    def achievement_contract_abi(self) -> dict:
        """Load Achievement contract ABI from file"""
        abi_path = Path(__file__).parent / "contracts" / "s-contracts" / "abi" / "AchievementToken.json"
        logger.info(f"Loading Achievement contract ABI from file: {abi_path}")
        return self._load_abi(abi_path)
    
    def _load_abi(self, path: Path) -> dict:
        """Helper method to load ABI from JSON file"""
        try:
            if not path.exists():
                raise FileNotFoundError(f"ABI file not found: {path}")
            with open(path, 'r') as f:
                contract_json = json.load(f)
                logger.info(f"Loaded ABI: {contract_json}")
            if isinstance(contract_json, dict) and 'abi' in contract_json:
                logger.info(f"Loaded ABI: {contract_json['abi']}")
                return contract_json['abi']
            return contract_json  # Assume the JSON itself is the ABI list

        except Exception as e:
            logging.error(f"Error loading ABI: {e}")
            return {}

@lru_cache()
def get_settings() -> Settings:
    """Cache settings instance for reuse"""
    return Settings()

# Create a singleton instance
settings = get_settings()