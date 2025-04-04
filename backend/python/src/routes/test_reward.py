from fastapi import APIRouter, Depends, HTTPException
from ..services.rewards.reward_service import RewardService

router = APIRouter(prefix="/test", tags=["testing"])

@router.post("/award-xp/{address}")
async def test_award_xp(address: str, reward_service: RewardService = Depends()):
    """Test endpoint for awarding XP to an address"""
    result = await reward_service.award_xp_for_contribution(address, 0.85)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return {"message": "XP awarded successfully", "details": result} 