from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import numpy as np
import os
from ...services.ml.asl_service import ASLService
from ...core.config import settings

# Initialize the model service with model path
model_path = settings.MODEL_PATH
asl_service = ASLService(model_path)

router = APIRouter(prefix="/prediction", tags=["prediction"])

class LandmarkRequest(BaseModel):
    landmarks: List[float]

class LabeledLandmarkRequest(BaseModel):
    landmarks: List[Dict[str, float]]
    label: str

class PredictionResponse(BaseModel):
    letter: str
    confidence: float
    landmarks: Optional[List[float]] = None

@router.post("/predict", response_model=PredictionResponse)
async def predict_sign(request: LandmarkRequest):
    """
    Predict the sign from hand landmarks
    """
    try:
        # Process landmarks using ASL service
        result = asl_service.process_landmarks(request.landmarks)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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