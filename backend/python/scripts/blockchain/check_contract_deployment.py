"""
Script to check contract deployment details and roles.
"""
import asyncio
import logging
import os
import sys

from web3 import Web3

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.config import settings
from services.blockchain.core import get_blockchain_service
from services.reward.xp_reward import Roles, XpRewardService

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    # Get the blockchain service
    blockchain = await get_blockchain_service()

    # Create XP reward service
    xp_service = XpRewardService(blockchain)

    # Print key information
    logger.info("=== Contract Deployment Check ===")
    logger.info(f"Service account address: {blockchain.account.address}")
    logger.info(f"Contract address: {xp_service.contract.address}")

    # Check MINTER_ROLE hash
    contract_minter_role = await xp_service.contract.functions.MINTER_ROLE().call()
    python_minter_role = Roles.MINTER_ROLE

    logger.info(f"Contract MINTER_ROLE hash: {contract_minter_role}")
    logger.info(f"Python MINTER_ROLE hash: {python_minter_role}")
    logger.info(
        f"MINTER_ROLE hashes match: {contract_minter_role == python_minter_role}"
    )

    # Check ADMIN_ROLE hash if it exists
    try:
        contract_admin_role = await xp_service.contract.functions.ADMIN_ROLE().call()
        logger.info(f"Contract ADMIN_ROLE hash: {contract_admin_role}")
    except Exception as e:
        logger.info("Contract does not expose ADMIN_ROLE directly")

    # Check DEFAULT_ADMIN_ROLE
    python_default_admin_role = Roles.DEFAULT_ADMIN_ROLE
    logger.info(f"Python DEFAULT_ADMIN_ROLE hash: {python_default_admin_role}")

    # Check who has the roles
    try:
        # Get the first few accounts with MINTER_ROLE (if any)
        # This is a simplified approach since we can't easily query all role holders
        logger.info("\n=== Checking known addresses for roles ===")

        # Check deployer address if we know it
        deployer = getattr(settings, "DEPLOYER_ADDRESS", None)
        if deployer:
            deployer = Web3.to_checksum_address(deployer)
            logger.info(f"Checking deployer address: {deployer}")

            has_minter = await xp_service.contract.functions.hasRole(
                contract_minter_role, deployer
            ).call()
            logger.info(f"Deployer has MINTER_ROLE: {has_minter}")

            has_admin = await xp_service.contract.functions.hasRole(
                python_default_admin_role, deployer
            ).call()
            logger.info(f"Deployer has DEFAULT_ADMIN_ROLE: {has_admin}")

        # Check service account
        logger.info(f"Checking service account: {blockchain.account.address}")
        has_minter = await xp_service.contract.functions.hasRole(
            contract_minter_role, blockchain.account.address
        ).call()
        logger.info(f"Service account has MINTER_ROLE: {has_minter}")

        has_admin = await xp_service.contract.functions.hasRole(
            python_default_admin_role, blockchain.account.address
        ).call()
        logger.info(f"Service account has DEFAULT_ADMIN_ROLE: {has_admin}")

    except Exception as e:
        logger.error(f"Error checking role assignments: {str(e)}")

    # Print environment variables
    logger.info("\n=== Environment Variables ===")
    logger.info(f"ERC20_XP_CONTRACT_ADDRESS: {settings.ERC20_XP_CONTRACT_ADDRESS}")
    logger.info(
        f"BLOCKCHAIN_PRIVATE_KEY: {'Set' if settings.BLOCKCHAIN_PRIVATE_KEY else 'Not set'}"
    )
    logger.info(
        f"REWARD_SERVICE_PRIVATE_KEY: {'Set' if getattr(settings, 'REWARD_SERVICE_PRIVATE_KEY', None) else 'Not set'}"
    )

    # Check which private key is being used
    if blockchain.account.address == Web3.to_checksum_address(
        getattr(settings, "DEPLOYER_ADDRESS", "0x0")
    ):
        logger.info("Service is using the DEPLOYER_ADDRESS")
    else:
        logger.info("Service is NOT using the DEPLOYER_ADDRESS")


if __name__ == "__main__":
    asyncio.run(main())
