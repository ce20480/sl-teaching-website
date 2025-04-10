"""
Test script for the V2 reward services.

This script tests the new V2 reward services that use the BaseContractService.
"""
import os
import sys
import logging
import asyncio
from typing import Dict, Any

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.blockchain.core import get_blockchain_service
from backend.python.src.services.reward.xp_reward import XpRewardServiceV2, get_xp_reward_service_v2, ActivityType
from backend.python.src.services.reward.achievement_reward import AchievementRewardServiceV2, get_achievement_reward_service_v2, AchievementType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_xp_reward_service():
    """Test the XpRewardServiceV2"""
    logger.info("Testing XpRewardServiceV2...")
    
    # Get the blockchain service
    blockchain = get_blockchain_service()
    
    # Create the XP reward service
    xp_service = XpRewardServiceV2(blockchain)
    
    # Test address - use a test address that you control
    test_address = "0x123456789012345678901234567890123456789a"  # Replace with a real address for testing
    
    # Check if the service has minter role
    has_minter_role = xp_service.check_minter_role()
    logger.info(f"Service has minter role: {has_minter_role}")
    
    if not has_minter_role:
        logger.warning("Service does not have minter role, some tests will fail")
    
    # Get the token balance
    try:
        balance = xp_service.get_token_balance(test_address)
        logger.info(f"Token balance for {test_address}: {balance}")
    except Exception as e:
        logger.error(f"Error getting token balance: {str(e)}")
    
    # Test award_xp (only if we have minter role)
    if has_minter_role:
        try:
            logger.info(f"Awarding XP to {test_address}...")
            result = xp_service.award_xp(test_address, ActivityType.LESSON_COMPLETION)
            logger.info(f"Award XP result: {result}")
            
            # Check transaction status
            if result.get('tx_hash'):
                tx_hash = result['tx_hash']
                logger.info(f"Checking transaction status for {tx_hash}...")
                await asyncio.sleep(5)  # Wait for transaction to be processed
                tx_status = xp_service.get_transaction_status(tx_hash)
                logger.info(f"Transaction status: {tx_status}")
        except Exception as e:
            logger.error(f"Error awarding XP: {str(e)}")
    
    # Test award_custom_xp (only if we have minter role)
    if has_minter_role:
        try:
            logger.info(f"Awarding custom XP to {test_address}...")
            result = xp_service.award_custom_xp(test_address, 10, ActivityType.QUIZ_COMPLETION)
            logger.info(f"Award custom XP result: {result}")
            
            # Check transaction status
            if result.get('tx_hash'):
                tx_hash = result['tx_hash']
                logger.info(f"Checking transaction status for {tx_hash}...")
                await asyncio.sleep(5)  # Wait for transaction to be processed
                tx_status = xp_service.get_transaction_status(tx_hash)
                logger.info(f"Transaction status: {tx_status}")
        except Exception as e:
            logger.error(f"Error awarding custom XP: {str(e)}")
    
    logger.info("XpRewardServiceV2 tests completed")

async def test_achievement_reward_service():
    """Test the AchievementRewardServiceV2"""
    logger.info("Testing AchievementRewardServiceV2...")
    
    # Get the blockchain service
    blockchain = get_blockchain_service()
    
    # Create the Achievement reward service
    achievement_service = AchievementRewardServiceV2(blockchain)
    
    # Test address - use a test address that you control
    test_address = "0x123456789012345678901234567890123456789a"  # Replace with a real address for testing
    
    # Test get_user_achievements
    try:
        achievements = achievement_service.get_user_achievements(test_address)
        logger.info(f"User achievements for {test_address}: {achievements}")
        
        # If the user has achievements, get details for the first one
        if achievements:
            token_id = achievements[0]
            achievement_details = achievement_service.get_achievement_details(token_id)
            logger.info(f"Achievement details for token {token_id}: {achievement_details}")
    except Exception as e:
        logger.error(f"Error getting user achievements: {str(e)}")
    
    # Test mint_achievement
    try:
        logger.info(f"Minting achievement for {test_address}...")
        result = achievement_service.mint_achievement(
            test_address, 
            AchievementType.BEGINNER, 
            "ipfs://QmTest", 
            "Test Achievement"
        )
        logger.info(f"Mint achievement result: {result}")
        
        # Check transaction status
        if result.get('tx_hash'):
            tx_hash = result['tx_hash']
            logger.info(f"Checking transaction status for {tx_hash}...")
            await asyncio.sleep(5)  # Wait for transaction to be processed
            tx_status = achievement_service.get_transaction_status(tx_hash)
            logger.info(f"Transaction status: {tx_status}")
    except Exception as e:
        logger.error(f"Error minting achievement: {str(e)}")
    
    # Test award_achievement_by_xp
    try:
        logger.info(f"Awarding achievement by XP for {test_address}...")
        result = achievement_service.award_achievement_by_xp(test_address, 100)  # 100 XP should qualify for BEGINNER
        logger.info(f"Award achievement by XP result: {result}")
        
        # Check transaction status
        if result.get('tx_hash'):
            tx_hash = result['tx_hash']
            logger.info(f"Checking transaction status for {tx_hash}...")
            await asyncio.sleep(5)  # Wait for transaction to be processed
            tx_status = achievement_service.get_transaction_status(tx_hash)
            logger.info(f"Transaction status: {tx_status}")
    except Exception as e:
        logger.error(f"Error awarding achievement by XP: {str(e)}")
    
    logger.info("AchievementRewardServiceV2 tests completed")

async def main():
    """Run all tests"""
    logger.info("Starting V2 reward services tests...")
    
    # Test XP reward service
    await test_xp_reward_service()
    
    # Test Achievement reward service
    await test_achievement_reward_service()
    
    logger.info("All tests completed")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(main())
