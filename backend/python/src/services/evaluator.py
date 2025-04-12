from typing import Dict, Any, Optional, Tuple
from enum import Enum
import asyncio
import os
import time
import logging
from pydantic import BaseModel

from .ml.blur_service import BlurService
from .ml.asl_service import ASLService
from ..core.config import settings

logger = logging.getLogger(__name__)

class EvaluationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"

class EvaluationResult(BaseModel):
    task_id: str
    status: EvaluationStatus
    message: Optional[str] = None
    score: Optional[float] = None
    completed: bool = False
    metadata: Dict[str, Any] = {}
    reward: Optional[Dict[str, Any]] = None

class EvaluatorService:
    """
    Service to evaluate user contributions using multiple evaluation criteria:
    1. Blur detection - Reject blurry images
    2. ASL landmark detection - Validate hand landmarks are present and detectable
    
    This service handles only the evaluation phase of the contribution workflow.
    Upload and reward phases are handled separately.
    """
    
    def __init__(self, asl_model_path=settings.MODEL_PATH, blur_threshold=100):
        # Initialize evaluation services
        self.blur_service = BlurService()
        
        # ASL service may be optional if model path not available
        self.asl_service = None
        if asl_model_path and os.path.exists(asl_model_path):
            logger.info(f"Initializing ASL service with model: {asl_model_path}")
            self.asl_service = ASLService(asl_model_path)
        else:
            logger.warning(f"ASL model not found at {asl_model_path}. ASL evaluation will be skipped.")
        
        # Setup processing queue
        self.processing_queue = asyncio.Queue()
        self._is_processing = False
        self.evaluations = {}
        
        # Evaluation thresholds
        self.blur_threshold = blur_threshold  # Minimum acceptable focus measure
    
    async def start_processing(self):
        """Start the background processing loop"""
        self._is_processing = True
        while self._is_processing:
            try:
                evaluation_task = await self.processing_queue.get()
                await self._process_evaluation(evaluation_task)
                self.processing_queue.task_done()
            except Exception as e:
                logger.error(f"Error processing evaluation: {e}")
    
    async def stop_processing(self):
        """Stop the background processing loop"""
        self._is_processing = False
    
    async def submit_for_evaluation(
        self,
        task_id: str,
        file_id: str,
        file_type: str,
        user_address: str,
        file_content: bytes,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Submit a file for evaluation
        
        Args:
            task_id: Unique ID for this evaluation
            file_id: ID of the uploaded file
            file_type: MIME type of the file
            user_address: Wallet address of the contributor
            file_content: Binary content of the file
            metadata: Additional file metadata
            
        Returns:
            Task ID for tracking
        """
        # Record submission time
        submission_time = time.time()
        
        self.evaluations[task_id] = EvaluationResult(
            task_id=task_id,
            status=EvaluationStatus.PENDING,
            message="Contribution pending evaluation",
            completed=False,
            metadata={
                "file_id": file_id,
                "file_type": file_type,
                "user_address": user_address,
                "submission_time": submission_time,
                **metadata
            }
        )
        
        # Add to queue for processing
        await self.processing_queue.put({
            "task_id": task_id,
            "file_content": file_content
        })
        
        return task_id
    
    async def _process_evaluation(self, task: Dict[str, Any]) -> EvaluationResult:
        """
        Process a single evaluation task using multiple criteria
        """
        task_id = task["task_id"]
        file_content = task.get("file_content", None)
        landmarks = task.get("landmarks", None)
        
        # Create result object if it doesn't exist
        if task_id not in self.evaluations:
            self.evaluations[task_id] = EvaluationResult(
                task_id=task_id,
                status=EvaluationStatus.PROCESSING,
                message="Processing contribution",
                completed=False,
                metadata={}
            )
        
        # Update status to processing
        self.evaluations[task_id].status = EvaluationStatus.PROCESSING
        self.evaluations[task_id].message = "Evaluating contribution quality"
        
        # Record evaluation start time
        evaluation_start_time = time.time()
        self.evaluations[task_id].metadata["evaluation_start_time"] = evaluation_start_time
        
        try:
            # 1. Check if image is blurry
            blur_result = await self._evaluate_blur(file_content)
            if not blur_result["success"]:
                self.evaluations[task_id].status = EvaluationStatus.REJECTED
                self.evaluations[task_id].message = f"Image rejected: {blur_result['message']}"
                self.evaluations[task_id].completed = True
                self.evaluations[task_id].metadata["evaluation_time"] = time.time()
                return self.evaluations[task_id]
                
            # 2. Check if hand landmarks are detectable
            landmark_result = await self._evaluate_landmarks(landmarks)
            if not landmark_result["success"]:
                self.evaluations[task_id].status = EvaluationStatus.REJECTED
                self.evaluations[task_id].message = f"Image rejected: {landmark_result['message']}"
                self.evaluations[task_id].completed = True
                self.evaluations[task_id].metadata["evaluation_time"] = time.time()
                return self.evaluations[task_id]
            
            # Calculate overall score based on evaluation results
            blur_score = blur_result.get("score", 0.5)
            landmark_score = landmark_result.get("score", 0.5)
            
            # Combined quality score (equal weighting)
            quality_score = (blur_score + landmark_score) / 2
            if quality_score < 0.5:
                self.evaluations[task_id].status = EvaluationStatus.REJECTED
                self.evaluations[task_id].message = "Contribution rejected: Quality score too low"
            else:
                # Set approval status and evaluation result
                self.evaluations[task_id].status = EvaluationStatus.APPROVED
                self.evaluations[task_id].message = "Contribution meets quality standards"

            self.evaluations[task_id].score = quality_score
            self.evaluations[task_id].completed = True

            # Record evaluation results and completion time
            evaluation_end_time = time.time()
            self.evaluations[task_id].metadata.update({
                "blur_score": blur_score,
                "landmark_score": landmark_score,
                "blur_details": blur_result,
                "landmark_details": landmark_result,
                "evaluation_time": evaluation_end_time,
                "evaluation_duration": evaluation_end_time - evaluation_start_time
            })
            
        except Exception as e:
            logger.error(f"Error during evaluation: {e}")
            self.evaluations[task_id].status = EvaluationStatus.FAILED
            self.evaluations[task_id].message = f"Evaluation failed: {str(e)}"
            self.evaluations[task_id].completed = True
            self.evaluations[task_id].metadata["evaluation_time"] = time.time()
            self.evaluations[task_id].metadata["error"] = str(e)
            
        return self.evaluations[task_id]
    
    async def _evaluate_blur(self, file_content: bytes) -> Dict[str, Any]:
        """Evaluate image for blurriness"""
        try:
            # Get focus measure from blur service
            focus_measure = self.blur_service.variance_of_laplacian_from_bytes(file_content)
            
            # Check if focus measure meets threshold
            is_blurry = focus_measure < self.blur_threshold
            
            if is_blurry:
                return {
                    "success": False,
                    "message": "Image is too blurry",
                    "focus_measure": focus_measure,
                    "threshold": self.blur_threshold
                }
            
            # Calculate normalized score (higher is better)
            # Scale between 0-1 with 1 being perfect focus
            normalized_score = min(1.0, focus_measure / (self.blur_threshold * 2))
            
            return {
                "success": True,
                "message": "Image has acceptable focus",
                "focus_measure": focus_measure,
                "score": normalized_score,
                "threshold": self.blur_threshold
            }
            
        except Exception as e:
            logger.error(f"Blur evaluation error: {e}")
            return {
                "success": False,
                "message": f"Blur evaluation failed: {str(e)}",
                "error": str(e)
            }
    
    async def _evaluate_landmarks(self, landmarks: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate if image contains detectable hand landmarks"""
        try:
            # Process landmarks using ASL service
            result = self.asl_service.process_landmarks(landmarks)
            
            # Return the result directly from ASL service
            if not result.get("success", False):
                logger.warning(f"Landmark evaluation failed: {result.get('message')}")
                return {
                    "success": False,
                    "message": result.get("message", "Hand landmark detection failed"),
                    "details": result
                }
                
            # Successful evaluation
            return {
                "success": True,
                "message": f"Hand landmarks detected, identified as letter '{result.get('letter')}'",
                "score": result.get("score", 0.5),
                "confidence": result.get("confidence", 0),
                "letter": result.get("letter", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Landmark evaluation error: {e}")
            return {
                "success": False,
                "message": f"Landmark evaluation failed: {str(e)}",
                "error": str(e)
            }
    
    async def get_evaluation_status(self, task_id: str) -> EvaluationResult:
        """Get the status of an evaluation"""
        if task_id not in self.evaluations:
            return EvaluationResult(
                task_id=task_id,
                status=EvaluationStatus.PENDING,
                message="Contribution pending evaluation",
                completed=False
            )
        return self.evaluations[task_id]

    async def update_evaluation_status(self, task_id: str, updated_result: EvaluationResult) -> EvaluationResult:
        """
        Update the status of an evaluation
        Update the status of apdate
        
        Arg
            task_id: Task ID to update
            updated_result: Updated result
        Returns:
            Updated evaluation result
        """
        if task_id not in self.evaluations:
            logger.warning(f"Attempted to update nonexistent evaluation: {task_id}")
            logger.warning(f"Attempted to update nonexistent e: {task_id}")
            return updated_result
        # Up
        # Update the stored evaluation
        self.evaluations[task_id] = updated_result
        logger.info(f"Updated evaluation status for task {task_id}: {updated_result.status}")
        return self.evaluations[task_id]