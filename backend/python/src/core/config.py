from functools import lru_cache
from pydantic_settings import BaseSettings
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
from pydantic import Field

# Load .env file once at startup
load_dotenv(Path(__file__).parent.parent.parent / ".env")

class Settings(BaseSettings):
    WEB3_PRIVATE_KEY: str
    NODE_ADDRESS: str = "connect.akave.ai:5500"
    DEFAULT_BUCKET: str = "asl-training-data"
    MODEL_PATH: str = Field(default="./models/asl_model.pkl")
    WEB3_PROVIDER_URL: str = Field(default="http://localhost:8545")
    ACHIEVEMENT_CONTRACT_ADDRESS: str = Field(default="")
    XP_TOKEN_CONTRACT_ADDRESS: str = Field(default="")
    REWARD_SERVICE_PRIVATE_KEY: str = Field(default="your_private_key_here")

    class Config:
        env_file = Path(__file__).parent.parent.parent / ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Cache settings instance for reuse"""
    return Settings()

# Create a singleton instance
settings = get_settings()