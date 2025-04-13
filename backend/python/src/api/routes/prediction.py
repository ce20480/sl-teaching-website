from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from ...services.service_container import get_asl_service
import logging
import json
logger = logging.getLogger(__name__)

# Initialize the model service with model path
asl_service = get_asl_service()

router = APIRouter(prefix="/prediction", tags=["prediction"])

class LandmarkRequest(BaseModel):
    landmarks: List[float]

class LabeledLandmarkRequest(BaseModel):
    landmarks: List[Dict[str, float]]
    label: str

class PredictionResponse(BaseModel):
    success: bool
    letter: str
    confidence: float
    score: float
    landmarks: Optional[List[float]] = None

@router.post("/predict", response_model=PredictionResponse)
async def predict_sign(request: LandmarkRequest):
    """
    Predict the sign from hand landmarks
    """
    try:
        logger.info(f"Received landmarks for prediction")
        
        # Validate landmarks
        if not request.landmarks or len(request.landmarks) < 3:
            # Return empty prediction with error indication
            logger.error("Invalid landmarks: empty or too few values")
            return PredictionResponse(
                success=False,
                letter="unknown",
                confidence=0.0,
                score=0.0,
                landmarks=request.landmarks
            )
        
        # Process landmarks using ASL service
        result = asl_service.process_landmarks(request.landmarks)
        
        if not result.get("success", False):
            # Log the error message
            error_msg = result.get("message", "Unknown error")
            logger.error(f"ASL service processing error: {error_msg}")
            
            # Return empty prediction with error handling
            return PredictionResponse(
                success=False,
                letter="error",
                confidence=0.0,
                score=0.0,
                landmarks=request.landmarks
            )
        
        # If successful, construct the correct response
        # Ensure all required fields are present
        return PredictionResponse(
            success=True,
            letter=result.get("letter", "unknown"),
            confidence=result.get("confidence", 0.0),
            score=result.get("score", 0.0),
            landmarks=result.get("landmarks", request.landmarks)
        )
    except Exception as e:
        logger.error(f"Error in prediction: {str(e)}")
        # Always return a valid PredictionResponse even for errors
        return PredictionResponse(
            success=False,
            letter="error",
            confidence=0.0,
            score=0.0,
            landmarks=request.landmarks if hasattr(request, 'landmarks') else []
        )

@router.post("/contribute")
async def contribute_landmarks(request: LabeledLandmarkRequest) -> Dict[str, Any]:
    """
    Store landmarks with label for model training
    """
    try:
        success = await asl_service.store_contribution(request.landmarks, request.label)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to store contribution")
            
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Export the router
prediction_router = router 