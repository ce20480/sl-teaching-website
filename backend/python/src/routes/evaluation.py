from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel
import uuid
from ..services.evaluation.evaluator import ContributionEvaluator
from ..services.rewards.reward_service import RewardService

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

class EvaluationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"

class EvaluationResponse(BaseModel):
    task_id: str
    status: EvaluationStatus
    message: Optional[str] = None
    score: Optional[float] = None
    completed: bool
    reward: Optional[Dict[str, Any]] = None

@router.get("/{task_id}", response_model=EvaluationResponse)
async def get_evaluation_status(
    task_id: str,
    evaluator: ContributionEvaluator = Depends()
):
    """Get the status of a contribution evaluation"""
    try:
        status = await evaluator.get_evaluation_status(task_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Evaluation not found: {str(e)}") 