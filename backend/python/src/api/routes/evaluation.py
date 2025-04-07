from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ...services.evaluator import ContributionEvaluator

router = APIRouter(prefix="/evaluation", tags=["evaluation"])
evaluator = ContributionEvaluator()

@router.get("/status/{task_id}")
async def get_evaluation_status(task_id: str) -> Dict[str, Any]:
    """
    Get the status of a contribution evaluation
    """
    try:
        status = await evaluator.get_evaluation_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Task ID {task_id} not found")
        
        return status
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))