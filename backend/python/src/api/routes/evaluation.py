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
            # Return a default pending status for unknown tasks
            return {
                "status": "pending",
                "message": "Task is queued for processing",
                "completed": False,
                "task_id": task_id
            }
        
        # Convert the EvaluationResult to a dictionary
        if hasattr(status, 'dict'):
            return status.dict()
        
        # If it's already a dict-like object, return it
        return status
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        elif "No evaluation found" in str(e):
            # Return a default pending status for unknown tasks
            return {
                "status": "pending",
                "message": "Task is queued for processing",
                "completed": False,
                "task_id": task_id
            }
        else:
            print(f"Error getting evaluation status: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))