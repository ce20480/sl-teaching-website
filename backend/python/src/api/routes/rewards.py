# api/routes/rewards.py
from fastapi import Depends, APIRouter, Query, Body, BackgroundTasks
from typing import Optional
import asyncio
import time

from ...services.reward.xp_reward import XpRewardService, get_xp_reward_service, ActivityType
from ...services.reward.achievement_reward import AchievementRewardService, get_achievement_reward_service, AchievementType

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
    # Use background task for fire-and-forget operation
    if background_tasks:
        # Start the transaction in the background
        # We'll store the task so we can get the result later if needed
        # task = background_tasks.add_task(xp_service.award_xp, address, activity_type)
        
        # Get current balance before the transaction is processed
        try:
            # Try to execute with automatic retry for nonce errors
            retry_count = 0
            result = None
            last_error = None
            
            while retry_count <= max_retries:
                try:
                    result = await asyncio.to_thread(xp_service.award_xp, address, activity_type)
                    
                    # Check if we got a nonce error that needs retry
                    if isinstance(result, dict) and result.get('status') == 'error' and result.get('error_category') == 'nonce_too_low':
                        retry_count += 1
                        if retry_count <= max_retries:
                            # Wait a bit before retrying (exponential backoff)
                            await asyncio.sleep(0.5 * (2 ** retry_count))
                            continue
                    
                    # If we got a rate limit error, wait longer and retry
                    if isinstance(result, dict) and result.get('error_category') == 'rate_limited':
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
                return {
                    "status": "processing", 
                    "message": "XP award initiated - check transaction status endpoint for confirmation", 
                    "address": address, 
                    "activity_type": activity_type.name,
                    "result": result,
                    "transaction_status": "pending",
                    "check_status_at": f"/rewards/xp/transactions/{address}",
                    "retries": retry_count
                }
            else:
                # If we don't have a result, return the last error
                return {
                    "error": last_error,
                    "status": "error", 
                    "message": f"XP award failed after {retry_count} retries", 
                    "address": address, 
                    "activity_type": activity_type.name,
                    "transaction_status": "failed",
                    "check_status_at": f"/rewards/xp/transactions/{address}"
                }
        except Exception as e:
            # If we can't get the balance, still return a response
            return {
                "error": str(e),
                "status": "error", 
                "message": "XP award failed with an unexpected error", 
                "address": address, 
                "activity_type": activity_type.name,
                "transaction_status": "failed",
                "check_status_at": f"/rewards/xp/transactions/{address}"
            }
    else:
        # Run synchronously in a thread pool to not block the event loop
        retry_count = 0
        result = None
        last_error = None
        
        while retry_count <= max_retries:
            try:
                result = await asyncio.to_thread(xp_service.award_xp, address, activity_type)
                
                # Check if we got a nonce error that needs retry
                if isinstance(result, dict) and result.get('status') == 'error' and result.get('error_category') == 'nonce_too_low':
                    retry_count += 1
                    if retry_count <= max_retries:
                        # Wait a bit before retrying (exponential backoff)
                        await asyncio.sleep(0.5 * (2 ** retry_count))
                        continue
                
                # If we got a rate limit error, wait longer and retry
                if isinstance(result, dict) and result.get('error_category') == 'rate_limited':
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
        
        # If we don't have a result, return the last error
        if not result:
            return {
                "error": last_error,
                "status": "error", 
                "message": f"XP award failed after {retry_count} retries", 
                "address": address, 
                "activity_type": activity_type.name,
                "transaction_status": "failed",
                "retries": retry_count
            }
        
        # Get updated balance after the transaction
        try:
            current_balance = await asyncio.to_thread(xp_service.get_token_balance, address)
            if isinstance(result, dict):
                result["current_balance"] = current_balance
                # Add a link to check transaction status
                if 'tx_hash' in result:
                    result["check_status_at"] = f"/rewards/xp/transaction/{result['tx_hash']}"
                result["retries"] = retry_count
        except Exception:
            # If we can't get the balance, just return the original result
            if isinstance(result, dict):
                result["retries"] = retry_count
        
        return result

@router.post("/xp/award-custom/{address}")
async def award_custom_xp(
    address: str,
    amount: int = Query(..., description="Custom amount of XP to award"),
    activity_type: ActivityType = Query(ActivityType.DATASET_CONTRIBUTION, description="Type of activity"),
    background_tasks: BackgroundTasks = None,
    xp_service: XpRewardService = Depends(get_xp_reward_service)
):
    """Award a custom amount of XP"""
    # Use background task for fire-and-forget operation
    if background_tasks:
        # Start the transaction in the background
        background_tasks.add_task(xp_service.award_custom_xp, address, amount, activity_type)
        
        # Get current balance before the transaction is processed
        try:
            current_balance = await asyncio.to_thread(xp_service.get_token_balance, address)
            return {
                "status": "processing", 
                "message": "Custom XP award initiated - check transaction status endpoint for confirmation", 
                "address": address, 
                "amount": amount,
                "activity_type": activity_type.name,
                "current_balance": current_balance,
                "transaction_status": "pending",
                "check_status_at": f"/rewards/xp/transactions/{address}"
            }
        except Exception as e:
            # If we can't get the balance, still return a response
            return {
                "status": "processing", 
                "message": "Custom XP award initiated, but couldn't fetch current balance - check transaction status endpoint", 
                "address": address, 
                "amount": amount,
                "activity_type": activity_type.name,
                "transaction_status": "pending",
                "check_status_at": f"/rewards/xp/transactions/{address}"
            }
    else:
        # Run synchronously in a thread pool to not block the event loop
        result = await asyncio.to_thread(xp_service.award_custom_xp, address, amount, activity_type)
        # Get updated balance after the transaction
        try:
            current_balance = await asyncio.to_thread(xp_service.get_token_balance, address)
            result["current_balance"] = current_balance
            # Add a link to check transaction status
            if 'tx_hash' in result:
                result["check_status_at"] = f"/rewards/xp/transaction/{result['tx_hash']}"
        except Exception:
            # If we can't get the balance, just return the original result
            pass
        return result

@router.put("/xp/update-rate")
async def update_reward_rate(
    activity_type: ActivityType = Query(..., description="Type of activity"),
    new_rate: int = Query(..., description="New reward rate"),
    xp_service: XpRewardService = Depends(get_xp_reward_service)
):
    """Update the reward rate for an activity type"""
    # This is an admin operation, so we'll wait for the result
    result = await asyncio.to_thread(xp_service.update_reward_rate, activity_type, new_rate)
    return result

# Legacy endpoint for backward compatibility
@router.post("/xp/mint/{address}")
async def mint_xp(
    address: str,
    amount: int = Query(..., description="Amount of XP to mint"),
    background_tasks: BackgroundTasks = None,
    xp_service: XpRewardService = Depends(get_xp_reward_service)
):
    """Legacy endpoint for minting XP tokens"""
    # Use background task for fire-and-forget operation
    if background_tasks:
        # Start the transaction in the background
        background_tasks.add_task(xp_service.mint, address, amount)
        
        # Get current balance before the transaction is processed
        try:
            current_balance = await asyncio.to_thread(xp_service.get_token_balance, address)
            return {
                "status": "processing", 
                "message": "XP mint initiated - check transaction status endpoint for confirmation", 
                "address": address, 
                "amount": amount,
                "current_balance": current_balance,
                "transaction_status": "pending",
                "check_status_at": f"/rewards/xp/transactions/{address}"
            }
        except Exception as e:
            # If we can't get the balance, still return a response
            return {
                "status": "processing", 
                "message": "XP mint initiated, but couldn't fetch current balance - check transaction status endpoint", 
                "address": address, 
                "amount": amount,
                "transaction_status": "pending",
                "check_status_at": f"/rewards/xp/transactions/{address}"
            }
    else:
        # Run synchronously in a thread pool to not block the event loop
        result = await asyncio.to_thread(xp_service.mint, address, amount)
        # Get updated balance after the transaction
        try:
            current_balance = await asyncio.to_thread(xp_service.get_token_balance, address)
            result["current_balance"] = current_balance
            # Add a link to check transaction status
            if 'tx_hash' in result:
                result["check_status_at"] = f"/rewards/xp/transaction/{result['tx_hash']}"
        except Exception:
            # If we can't get the balance, just return the original result
            pass
        return result

# XP Balance Endpoint

@router.get("/xp/balance/{address}")
async def get_xp_balance(
    address: str,
    xp_service: XpRewardService = Depends(get_xp_reward_service)
):
    """Get the current XP token balance for an address"""
    balance = await asyncio.to_thread(xp_service.get_token_balance, address)
    return {
        "address": address,
        "balance": balance,
        "timestamp": int(time.time())
    }

@router.get("/xp/transactions/{address}")
async def get_address_transactions(
    address: str,
    xp_service: XpRewardService = Depends(get_xp_reward_service)
):
    """Get recent XP token transactions for an address
    
    This endpoint allows clients to check the status of pending transactions
    and verify if tokens were successfully awarded.
    """
    transactions = await asyncio.to_thread(xp_service.get_address_transactions, address)
    
    # Get current balance to include in the response
    try:
        current_balance = await asyncio.to_thread(xp_service.get_token_balance, address)
        balance_info = {"current_balance": current_balance}
    except Exception as e:
        balance_info = {"balance_error": str(e)}
    
    return {
        "address": address,
        "transactions": transactions,
        "timestamp": int(time.time()),
        **balance_info
    }

@router.get("/xp/transaction/{tx_hash}")
async def get_transaction_status(
    tx_hash: str,
    xp_service: XpRewardService = Depends(get_xp_reward_service)
):
    """Get the status of a specific transaction
    
    This endpoint allows clients to check if a specific transaction has been confirmed
    and whether tokens were successfully awarded.
    """
    status = await asyncio.to_thread(xp_service.get_transaction_status, tx_hash)
    
    # If we have an address in the transaction details, get the current balance
    if 'address' in status:
        try:
            address = status['address']
            current_balance = await asyncio.to_thread(xp_service.get_token_balance, address)
            status["current_balance"] = current_balance
        except Exception as e:
            status["balance_error"] = str(e)
    
    return {
        "tx_hash": tx_hash,
        **status,
        "timestamp": int(time.time())
    }

# Achievement Reward Endpoints

@router.post("/achievement/mint")
async def mint_achievement(
    address: str = Query(..., description="Address to receive the achievement"),
    achievement_type: AchievementType = Query(..., description="Type of achievement"),
    ipfs_hash: str = Query(..., description="IPFS hash for metadata"),
    description: str = Query(..., description="Description of the achievement"),
    background_tasks: BackgroundTasks = None,
    achievement_service: AchievementRewardService = Depends(get_achievement_reward_service)
):
    """Mint a new achievement token"""
    # Use background task for fire-and-forget operation
    if background_tasks:
        background_tasks.add_task(achievement_service.mint_achievement, address, achievement_type, ipfs_hash, description)
        return {"status": "processing", "message": "Achievement mint initiated", "address": address, "achievement_type": achievement_type.name}
    else:
        # Run synchronously in a thread pool to not block the event loop
        result = await asyncio.to_thread(achievement_service.mint_achievement, address, achievement_type, ipfs_hash, description)
        return result

@router.put("/achievement/update-metadata/{token_id}")
async def update_achievement_metadata(
    token_id: int,
    new_ipfs_hash: str = Query(..., description="New IPFS hash"),
    achievement_service: AchievementRewardService = Depends(get_achievement_reward_service)
):
    """Update the IPFS hash for a token's metadata"""
    # This is an admin operation, so we'll wait for the result
    result = await asyncio.to_thread(achievement_service.update_metadata, token_id, new_ipfs_hash)
    return result

@router.get("/achievement/user/{address}")
async def get_user_achievements(
    address: str,
    achievement_service: AchievementRewardService = Depends(get_achievement_reward_service)
):
    """Get all achievements for a user"""
    # Read operations should be quick, but still use to_thread to avoid blocking
    result = await asyncio.to_thread(achievement_service.get_user_achievements, address)
    return {"token_ids": result}

@router.get("/achievement/{token_id}")
async def get_achievement(
    token_id: int,
    achievement_service: AchievementRewardService = Depends(get_achievement_reward_service)
):
    """Get achievement details for a specific token"""
    # Read operations should be quick, but still use to_thread to avoid blocking
    result = await asyncio.to_thread(achievement_service.get_achievement, token_id)
    return result

@router.post("/achievement/award/{address}")
async def award_achievement(
    address: str,
    total_xp: int = Query(..., description="Total XP to determine achievement level"),
    background_tasks: BackgroundTasks = None,
    achievement_service: AchievementRewardService = Depends(get_achievement_reward_service)
):
    """Award achievement based on total XP"""
    # Use background task for fire-and-forget operation
    if background_tasks:
        background_tasks.add_task(achievement_service.award_achievement, address, total_xp)
        return {"status": "processing", "message": "Achievement award initiated", "address": address, "total_xp": total_xp}
    else:
        # Run synchronously in a thread pool to not block the event loop
        result = await asyncio.to_thread(achievement_service.award_achievement, address, total_xp)
        return result