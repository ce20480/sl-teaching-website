"""
Script to check and grant MINTER_ROLE to an address.
This is useful when the deployer address needs to mint tokens.
"""
import asyncio
import sys
import os
import logging
from web3 import Web3

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.blockchain.core import get_blockchain_service
from services.reward.xp_reward import XpRewardService, Roles
from core.config import settings

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
    
    # Address to check/grant role to (default to the account being used)
    target_address = blockchain.account.address
    
    # Check if an address was provided as a command line argument
    if len(sys.argv) > 1:
        target_address = Web3.to_checksum_address(sys.argv[1])
    
    logger.info(f"Checking roles for address: {target_address}")
    
    # Check if the address has DEFAULT_ADMIN_ROLE
    try:
        has_admin = await xp_service.contract.functions.hasRole(
            Roles.DEFAULT_ADMIN_ROLE,
            target_address
        ).call()
        
        logger.info(f"Has DEFAULT_ADMIN_ROLE: {has_admin}")
        
        # Check if the address has MINTER_ROLE
        has_minter = await xp_service.contract.functions.hasRole(
            Roles.MINTER_ROLE,
            target_address
        ).call()
        
        logger.info(f"Has MINTER_ROLE: {has_minter}")
        
        # If the address doesn't have MINTER_ROLE but has admin role, grant it
        if not has_minter:
            if has_admin:
                logger.info(f"Granting MINTER_ROLE to {target_address}...")
                result = await xp_service.grant_minter_role(target_address)
                
                if result.get('status') == 'success':
                    logger.info(f"Successfully granted MINTER_ROLE. Transaction: {result.get('tx_hash')}")
                else:
                    logger.error(f"Failed to grant MINTER_ROLE: {result.get('error')}")
            else:
                logger.error(f"Address {target_address} does not have DEFAULT_ADMIN_ROLE and cannot be granted MINTER_ROLE")
                logger.info("You need to use an address with DEFAULT_ADMIN_ROLE to grant MINTER_ROLE")
        else:
            logger.info(f"Address {target_address} already has MINTER_ROLE")
    
    except Exception as e:
        logger.error(f"Error checking/granting roles: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
