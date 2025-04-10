# api/routes/rewards.py
from fastapi import Depends, APIRouter, Query, BackgroundTasks
import asyncio
import time
import logging

from ...services.reward.xp_reward import XpRewardService, get_xp_reward_service, ActivityType
from ...services.reward.achievement_reward import AchievementRewardService, get_achievement_reward_service, AchievementType

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rewards", tags=["rewards"])

# XP Reward Endpoints

@router.post("/xp/award/{address}")
async def award_xp(
    address: str,
    activity_type: ActivityType = Query(ActivityType.DATASET_CONTRIBUTION, description="Type of activity"),
    background_tasks: BackgroundTasks = None,
    xp_service: XpRewardService = Depends(get_xp_reward_service),
    max_retries: int = 3
):
    """Award XP based on predefined activity type"""
    try:
        # Log the request
        logger.info(f"Received request to award XP to {address} for activity {activity_type}")
        
        
        # Try to execute with automatic retry for nonce errors
        retry_count = 0
        result = None
        last_error = None
        
        while retry_count <= max_retries:
            try:
                # Use asyncio.to_thread to run the synchronous method in a separate thread
                logger.info(f"Attempting to award XP to {address} (attempt {retry_count+1}/{max_retries+1})")
                result = await asyncio.to_thread(xp_service.award_xp, address, activity_type)
                
                # Check if we got a nonce error that needs retry
                if isinstance(result, dict) and result.get('status') == 'error':
                    error_category = result.get('error_category')
                    error_message = result.get('error', 'Unknown error')
                    logger.warning(f"Error awarding XP: {error_message} (category: {error_category})")
                    
                    if error_category == 'nonce_too_low' or error_category == 'nonce_error':
                        retry_count += 1
                        if retry_count <= max_retries:
                            logger.info(f"Retrying due to nonce error (attempt {retry_count+1}/{max_retries+1})")
                            # Wait a bit before retrying (exponential backoff)
                            await asyncio.sleep(0.5 * (2 ** retry_count))
                            continue
                    
                    # If we got a rate limit error, wait longer and retry
                    if error_category == 'rate_limited':
                        retry_count += 1
                        if retry_count <= max_retries:
                            # Wait longer for rate limit errors
                            await asyncio.sleep(2 * (2 ** retry_count))
                            continue
                
                # If we get here, either the transaction succeeded or we got a different error
                break
                
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                if retry_count <= max_retries:
                    # Wait a bit before retrying
                    await asyncio.sleep(0.5 * (2 ** retry_count))
                else:
                    break
        
        # If we have a result, return it
        if result:
            # Add helpful information to the response
            response = {
                "status": "processing" if result.get('status') == 'success' else result.get('status', 'error'), 
                "message": "XP award initiated - check transaction status endpoint for confirmation" if result.get('status') == 'success' else result.get('error', 'Unknown error'),
                "address": address, 
                "activity_type": activity_type.name,
                "transaction_status": "pending" if result.get('status') == 'success' else "failed",
                "retries": retry_count,
                "result": result
            }
            
            # Add transaction hash if available
            if result.get('tx_hash'):
                response["tx_hash"] = result['tx_hash']
                response["check_status_at"] = f"/rewards/v2/transactions/{result['tx_hash']}"
            
            return response
        else:
            # If we don't have a result, return the last error
            return {
                "error": last_error,
                "status": "error", 
            }
    except Exception as e:
        logger.error(f"Unexpected error in award_xp endpoint: {str(e)}", exc_info=True)
        
        # Determine error category based on exception type
        error_category = 'unexpected_error'
        if 'contract' in str(e).lower():
            error_category = 'contract_error'
        elif 'abi' in str(e).lower():
            error_category = 'abi_error'
        elif 'address' in str(e).lower():
            error_category = 'address_error'
        elif 'permission' in str(e).lower() or 'role' in str(e).lower():
            error_category = 'permission_error'
        
        # Return error response with more details
        return {
            'status': 'error',
            'error': str(e),
            'error_category': error_category,
            'timestamp': int(time.time())
        }


@router.post("/xp/award-custom/{address}")
async def award_custom_xp(
    address: str,
    amount: int = Query(..., description="Custom amount of XP to award"),
    activity_type: ActivityType = Query(ActivityType.DATASET_CONTRIBUTION, description="Type of activity"),
    background_tasks: BackgroundTasks = None,
    xp_service: XpRewardService = Depends(get_xp_reward_service),
    max_retries: int = 3
):
    """Award a custom amount of XP"""
    try:
        # Validate amount
        if amount <= 0:
            return {
                "status": "error",
                "message": "Amount must be positive",
                "address": address,
                "amount": amount
            }
        
        # Try to execute with automatic retry for nonce errors
        retry_count = 0
        result = None
        last_error = None
        
        while retry_count <= max_retries:
            try:
                # Use asyncio.to_thread to run the synchronous method in a separate thread
                result = await asyncio.to_thread(xp_service.award_custom_xp, address, amount, activity_type)
                
                # Check if we got a nonce error that needs retry
                if isinstance(result, dict) and result.get('status') == 'error':
                    error_category = result.get('error_category')
                    if error_category == 'nonce_too_low' or error_category == 'nonce_error':
                        retry_count += 1
                        if retry_count <= max_retries:
                            # Wait a bit before retrying (exponential backoff)
                            await asyncio.sleep(0.5 * (2 ** retry_count))
                            continue
                    
                    # If we got a rate limit error, wait longer and retry
                    if error_category == 'rate_limited':
                        retry_count += 1
                        if retry_count <= max_retries:
                            # Wait longer for rate limit errors
                            await asyncio.sleep(2 * (2 ** retry_count))
                            continue
                
                # If we get here, either the transaction succeeded or we got a different error
                break
                
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                if retry_count <= max_retries:
                    # Wait a bit before retrying
                    await asyncio.sleep(0.5 * (2 ** retry_count))
                else:
                    break
        
        # If we have a result, return it
        if result:
            # Add helpful information to the response
            response = {
                "status": "processing" if result.get('status') == 'success' else result.get('status', 'error'), 
                "message": "Custom XP award initiated - check transaction status endpoint for confirmation" if result.get('status') == 'success' else result.get('error', 'Unknown error'),
                "address": address, 
                "amount": amount,
                "activity_type": activity_type.name,
                "transaction_status": "pending" if result.get('status') == 'success' else "failed",
                "retries": retry_count,
                "result": result
            }
            
            # Add transaction hash if available
            if result.get('tx_hash'):
                response["tx_hash"] = result['tx_hash']
                response["check_status_at"] = f"/rewards/v2/transactions/{result['tx_hash']}"
            
            return response
        else:
            # If we don't have a result, return the last error
            return {
                "error": last_error,
                "status": "error", 
                "message": f"Custom XP award failed after {retry_count} retries", 
                "address": address, 
                "amount": amount,
                "activity_type": activity_type.name,
                "transaction_status": "failed"
            }
    except Exception as e:
        logger.error(f"Unexpected error in award_custom_xp endpoint: {str(e)}")
        # If we can't process the request, return an error
        return {
            "error": str(e),
            "status": "error", 
            "message": "Custom XP award failed with an unexpected error", 
            "address": address, 
            "amount": amount,
            "activity_type": activity_type.name,
            "transaction_status": "failed"
        }


@router.post("/xp/update-reward-rate")
async def update_reward_rate(
    activity_type: ActivityType = Query(..., description="Type of activity"),
    new_rate: int = Query(..., description="New reward rate"),
    xp_service: XpRewardService = Depends(get_xp_reward_service)
):
    """Update the reward rate for an activity type"""
    try:
        # Validate new rate
        if new_rate <= 0:
            return {
                "status": "error",
                "message": "New rate must be positive",
                "activity_type": activity_type.name,
                "new_rate": new_rate
            }
        
        # Call the service method
        result = await asyncio.to_thread(xp_service.update_reward_rate, activity_type, new_rate)
        
        # Add helpful information to the response
        response = {
            "status": "processing" if result.get('status') == 'success' else result.get('status', 'error'), 
            "message": "Reward rate update initiated" if result.get('status') == 'success' else result.get('error', 'Unknown error'),
            "activity_type": activity_type.name,
            "new_rate": new_rate,
            "transaction_status": "pending" if result.get('status') == 'success' else "failed",
            "result": result
        }
        
        # Add transaction hash if available
        if result.get('tx_hash'):
            response["tx_hash"] = result['tx_hash']
            response["check_status_at"] = f"/rewards/v2/transactions/{result['tx_hash']}"
        
        return response
    except Exception as e:
        logger.error(f"Unexpected error in update_reward_rate endpoint: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to update reward rate: {str(e)}",
            "activity_type": activity_type.name,
            "new_rate": new_rate
        }


# Legacy endpoint for backward compatibility
@router.post("/xp/mint/{address}")
async def mint_xp(
    address: str,
    amount: int = Query(..., description="Amount of XP to mint"),
    background_tasks: BackgroundTasks = None,
    xp_service: XpRewardService = Depends(get_xp_reward_service),
    max_retries: int = 3
):
    """Legacy endpoint for minting XP tokens"""
    # This is just a wrapper around award_custom_xp with DATASET_CONTRIBUTION activity type
    return await award_custom_xp(
        address=address,
        amount=amount,
        activity_type=ActivityType.DATASET_CONTRIBUTION,
        background_tasks=background_tasks,
        xp_service=xp_service,
        max_retries=max_retries
    )


# XP Balance Endpoint
@router.get("/xp/balance/{address}")
async def get_xp_balance(
    address: str,
    xp_service: XpRewardService = Depends(get_xp_reward_service)
):
    """Get the current XP token balance for an address"""
    try:
        # Call the service method
        balance = await asyncio.to_thread(xp_service.get_token_balance, address)
        
        return {
            "status": "success",
            "address": address,
            "balance": balance
        }
    except Exception as e:
        logger.error(f"Error getting XP balance: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get XP balance: {str(e)}",
            "address": address
        }


@router.get("/transactions/{tx_hash}")
async def get_transaction_status(
    tx_hash: str,
    xp_service: XpRewardService = Depends(get_xp_reward_service)
):
    """
    Get the status of a specific transaction
    
    This endpoint allows clients to check if a specific transaction has been confirmed
    and whether tokens were successfully awarded.
    """
    try:
        # Get transaction status from the transaction manager via the service
        tx_status = await asyncio.to_thread(xp_service.get_transaction_status, tx_hash)
        
        if tx_status:
            return {
                "status": "success",
                "tx_hash": tx_hash,
                "transaction_status": tx_status
            }
        else:
            return {
                "status": "error",
                "message": f"Transaction {tx_hash} not found",
                "tx_hash": tx_hash
            }
    except Exception as e:
        logger.error(f"Error getting transaction status: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get transaction status: {str(e)}",
            "tx_hash": tx_hash
        }


# Achievement Reward Endpoints
@router.post("/achievements/mint/{address}")
async def mint_achievement(
    address: str,
    achievement_type: AchievementType = Query(..., description="Type of achievement"),
    ipfs_hash: str = Query("", description="IPFS hash for metadata"),
    description: str = Query("", description="Description of the achievement"),
    background_tasks: BackgroundTasks = None,
    achievement_service: AchievementRewardService = Depends(get_achievement_reward_service),
    max_retries: int = 3
):
    """Mint a new achievement token"""
    try:
        # Try to execute with automatic retry for nonce errors
        retry_count = 0
        result = None
        last_error = None
        
        while retry_count <= max_retries:
            try:
                # Use asyncio.to_thread to run the synchronous method in a separate thread
                result = await asyncio.to_thread(
                    achievement_service.mint_achievement, 
                    address, 
                    achievement_type, 
                    ipfs_hash, 
                    description or f"{achievement_type.name} Achievement"
                )
                
                # Check if we got a nonce error that needs retry
                if isinstance(result, dict) and result.get('status') == 'error':
                    error_category = result.get('error_category')
                    if error_category == 'nonce_too_low' or error_category == 'nonce_error':
                        retry_count += 1
                        if retry_count <= max_retries:
                            # Wait a bit before retrying (exponential backoff)
                            await asyncio.sleep(0.5 * (2 ** retry_count))
                            continue
                    
                    # If we got a rate limit error, wait longer and retry
                    if error_category == 'rate_limited':
                        retry_count += 1
                        if retry_count <= max_retries:
                            # Wait longer for rate limit errors
                            await asyncio.sleep(2 * (2 ** retry_count))
                            continue
                
                # If we get here, either the transaction succeeded or we got a different error
                break
                
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                if retry_count <= max_retries:
                    # Wait a bit before retrying
                    await asyncio.sleep(0.5 * (2 ** retry_count))
                else:
                    break
        
        # If we have a result, return it
        if result:
            # Add helpful information to the response
            response = {
                "status": "processing" if result.get('status') == 'success' else result.get('status', 'error'), 
                "message": "Achievement minting initiated" if result.get('status') == 'success' else result.get('error', 'Unknown error'),
                "address": address, 
                "achievement_type": achievement_type.name,
                "transaction_status": "pending" if result.get('status') == 'success' else "failed",
                "retries": retry_count,
                "result": result
            }
            
            # Add transaction hash if available
            if result.get('tx_hash'):
                response["tx_hash"] = result['tx_hash']
                response["check_status_at"] = f"/rewards/v2/transactions/{result['tx_hash']}"
            
            # Add token ID if available
            if result.get('token_id') is not None:
                response["token_id"] = result['token_id']
            
            return response
        else:
            # If we don't have a result, return the last error
            return {
                "error": last_error,
                "status": "error", 
                "message": f"Achievement minting failed after {retry_count} retries", 
                "address": address, 
                "achievement_type": achievement_type.name,
                "transaction_status": "failed"
            }
    except Exception as e:
        logger.error(f"Unexpected error in mint_achievement endpoint: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to mint achievement: {str(e)}",
            "address": address,
            "achievement_type": achievement_type.name
        }


@router.post("/achievements/update-metadata/{token_id}")
async def update_achievement_metadata(
    token_id: int,
    new_ipfs_hash: str = Query(..., description="New IPFS hash"),
    achievement_service: AchievementRewardService = Depends(get_achievement_reward_service)
):
    """Update the IPFS hash for a token's metadata"""
    try:
        # Call the service method
        result = await asyncio.to_thread(achievement_service.update_metadata, token_id, new_ipfs_hash)
        
        # Add helpful information to the response
        response = {
            "status": "processing" if result.get('status') == 'success' else result.get('status', 'error'), 
            "message": "Metadata update initiated" if result.get('status') == 'success' else result.get('error', 'Unknown error'),
            "token_id": token_id,
            "new_ipfs_hash": new_ipfs_hash,
            "transaction_status": "pending" if result.get('status') == 'success' else "failed",
            "result": result
        }
        
        # Add transaction hash if available
        if result.get('tx_hash'):
            response["tx_hash"] = result['tx_hash']
            response["check_status_at"] = f"/rewards/v2/transactions/{result['tx_hash']}"
        
        return response
    except Exception as e:
        logger.error(f"Unexpected error in update_achievement_metadata endpoint: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to update metadata: {str(e)}",
            "token_id": token_id,
            "new_ipfs_hash": new_ipfs_hash
        }


@router.get("/achievements/user/{address}")
async def get_user_achievements(
    address: str,
    achievement_service: AchievementRewardService = Depends(get_achievement_reward_service)
):
    """Get all achievements for a user"""
    try:
        # Call the service method
        achievements = await asyncio.to_thread(achievement_service.get_user_achievement_details, address)
        
        return {
            "status": "success",
            "address": address,
            "achievements": achievements
        }
    except Exception as e:
        logger.error(f"Error getting user achievements: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get user achievements: {str(e)}",
            "address": address
        }


@router.get("/achievements/{token_id}")
async def get_achievement(
    token_id: int,
    achievement_service: AchievementRewardService = Depends(get_achievement_reward_service)
):
    """Get achievement details for a specific token"""
    try:
        # Call the service method
        achievement = await asyncio.to_thread(achievement_service.get_achievement_details, token_id)
        
        return {
            "status": "success",
            "token_id": token_id,
            "achievement": achievement
        }
    except Exception as e:
        logger.error(f"Error getting achievement details: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get achievement details: {str(e)}",
            "token_id": token_id
        }


@router.post("/achievements/award-by-xp/{address}")
async def award_achievement(
    address: str,
    total_xp: int = Query(..., description="Total XP to determine achievement level"),
    ipfs_hash: str = Query("", description="IPFS hash for metadata"),
    background_tasks: BackgroundTasks = None,
    achievement_service: AchievementRewardService = Depends(get_achievement_reward_service),
    max_retries: int = 3
):
    """Award achievement based on total XP"""
    try:
        # Try to execute with automatic retry for nonce errors
        retry_count = 0
        result = None
        last_error = None
        
        while retry_count <= max_retries:
            try:
                # Use asyncio.to_thread to run the synchronous method in a separate thread
                result = await asyncio.to_thread(
                    achievement_service.award_achievement_by_xp, 
                    address, 
                    total_xp,
                    ipfs_hash
                )
                
                # Check if we got a nonce error that needs retry
                if isinstance(result, dict) and result.get('status') == 'error':
                    error_category = result.get('error_category')
                    if error_category == 'nonce_too_low' or error_category == 'nonce_error':
                        retry_count += 1
                        if retry_count <= max_retries:
                            # Wait a bit before retrying (exponential backoff)
                            await asyncio.sleep(0.5 * (2 ** retry_count))
                            continue
                    
                    # If we got a rate limit error, wait longer and retry
                    if error_category == 'rate_limited':
                        retry_count += 1
                        if retry_count <= max_retries:
                            # Wait longer for rate limit errors
                            await asyncio.sleep(2 * (2 ** retry_count))
                            continue
                
                # If we get here, either the transaction succeeded or we got a different error
                break
                
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                if retry_count <= max_retries:
                    # Wait a bit before retrying
                    await asyncio.sleep(0.5 * (2 ** retry_count))
                else:
                    break
        
        # If we have a result, return it
        if result:
            # Add helpful information to the response
            response = {
                "status": "processing" if result.get('status') == 'success' else result.get('status', 'error'), 
                "message": "Achievement award initiated" if result.get('status') == 'success' else result.get('error', 'Unknown error'),
                "address": address, 
                "total_xp": total_xp,
                "transaction_status": "pending" if result.get('status') == 'success' else "failed",
                "retries": retry_count,
                "result": result
            }
            
            # Add transaction hash if available
            if result.get('tx_hash'):
                response["tx_hash"] = result['tx_hash']
                response["check_status_at"] = f"/rewards/v2/transactions/{result['tx_hash']}"
            
            # Add token ID if available
            if result.get('token_id') is not None:
                response["token_id"] = result['token_id']
            
            return response
        else:
            # If we don't have a result, return the last error
            return {
                "error": last_error,
                "status": "error", 
                "message": f"Achievement award failed after {retry_count} retries", 
                "address": address, 
                "total_xp": total_xp,
                "transaction_status": "failed"
            }
    except Exception as e:
        logger.error(f"Unexpected error in award_achievement endpoint: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to award achievement: {str(e)}",
            "address": address,
            "total_xp": total_xp
        }
