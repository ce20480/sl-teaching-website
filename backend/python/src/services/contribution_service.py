from typing import Dict, Any, Optional
import logging
import time
import uuid

from .evaluator import EvaluatorService, EvaluationStatus
from .storage.akave_sdk import AkaveSDK
from .reward.xp_reward import XpRewardService, ActivityType

logger = logging.getLogger(__name__)

class ContributionService:
    """
    Service to coordinate the three-phase contribution workflow:
    1. Evaluate image quality
    2. Upload approved images
    3. Reward users for approved contributions
    
    This service acts as an orchestrator between the different specialized services.
    """
    
    def __init__(self, evaluator: EvaluatorService, storage_sdk: AkaveSDK, reward_service: XpRewardService, default_bucket: str):
        self.evaluator = evaluator
        self.storage_sdk = storage_sdk
        self.reward_service = reward_service
        self.default_bucket = default_bucket
        
    async def submit_contribution(
        self, 
        file_content: bytes, 
        file_name: str, 
        file_type: str, 
        user_address: str
    ) -> Dict[str, Any]:
        """
        Submit a contribution for processing
        
        Args:
            file_content: Binary content of the file
            file_name: Original filename
            file_type: MIME type of the file
            user_address: User's wallet address
            
        Returns:
            Task metadata with IDs for tracking
        """
        # Generate unique IDs
        file_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        file_size = len(file_content)
        
        # Create task metadata
        task_metadata = {
            "task_id": task_id,
            "file_id": file_id,
            "filename": file_name,
            "file_size": file_size,
            "content_type": file_type,
            "user_address": user_address,
            "submission_time": time.time(),
            "evaluation_time": None,
            "upload_time": None,
            "reward_time": None
        }
        
        logger.info(f"Submitted file for evaluation: {file_name}, size: {file_size} bytes")
        
        # Submit file for evaluation
        await self.evaluator.submit_for_evaluation(
            task_id=task_id,
            file_id=file_id,
            file_type=file_type,
            user_address=user_address,
            file_content=file_content,
            metadata={
                "filename": file_name,
                "content_type": file_type,
                "size": file_size,
            }
        )
        
        return task_metadata
        
    async def process_evaluation_workflow(
        self,
        task_id: str,
        user_address: str,
        file_content: bytes,
        task_metadata: Dict[str, Any]
    ):
        """
        Orchestrates the three-phase evaluation, upload, and reward workflow.
        
        Args:
            task_id: Unique ID for the evaluation task
            user_address: User's wallet address
            file_content: Binary content of the file
            task_metadata: Additional metadata about the task
        """
        try:
            logger.info(f"Starting evaluation phase for task ID: {task_id}")
            
            # Phase 1: Evaluate image quality
            evaluation_result = await self.process_evaluation_phase(task_id, file_content, task_metadata)
            
            # Only proceed if evaluation was approved
            if evaluation_result.status == EvaluationStatus.APPROVED:
                logger.info(f"Evaluation approved for task ID: {task_id}, proceeding to upload phase")
                
                # Phase 2: Upload to storage
                upload_result = await self.process_upload_phase(task_id, file_content, task_metadata)
                
                if upload_result.get("success"):
                    logger.info(f"Upload successful for task ID: {task_id}, proceeding to reward phase")
                    
                    # Phase 3: Reward user
                    await self.process_reward_phase(task_id, user_address, upload_result, task_metadata)
            else:
                logger.info(f"Evaluation rejected for task ID: {task_id}, workflow stopped")
        
        except Exception as e:
            logger.error(f"Error in evaluation workflow for task ID {task_id}: {e}")
            # Update evaluation status to failed
            evaluation = await self.evaluator.get_evaluation_status(task_id)
            if evaluation:
                evaluation.status = EvaluationStatus.FAILED
                evaluation.message = f"Workflow failed: {str(e)}"
                evaluation.completed = True

    async def process_evaluation_phase(
        self,
        task_id: str, 
        file_content: bytes,
        task_metadata: Dict[str, Any]
    ) -> Any:
        """
        Process the evaluation phase of the workflow.
        
        Args:
            task_id: Unique ID for the evaluation task
            file_content: Binary content of the file
            task_metadata: Additional metadata about the task
            
        Returns:
            Evaluation result
        """
        try:
            # Run the evaluation
            result = await self.evaluator._process_evaluation({
                "task_id": task_id,
                "file_content": file_content
            })
            
            # Update metadata
            task_metadata["evaluation_time"] = result.metadata.get("evaluation_time")
            
            return result
        except Exception as e:
            logger.error(f"Error in evaluation phase for task ID {task_id}: {e}")
            raise

    async def process_upload_phase(
        self,
        task_id: str, 
        file_content: bytes,
        task_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process the upload phase of the workflow.
        
        Args:
            task_id: Unique ID for the evaluation task
            file_content: Binary content of the file
            task_metadata: Additional metadata about the task
            
        Returns:
            Upload result
        """
        try:
            file_name = task_metadata.get("filename", f"upload_{task_id}.jpg")
            
            # Upload to storage
            async with self.storage_sdk as client:
                upload_result = await client.upload_file(
                    bucket_name=self.default_bucket,
                    file_data=file_content,
                    file_name=file_name
                )
                
                # Update evaluation metadata with storage details
                evaluation = await self.evaluator.get_evaluation_status(task_id)
                if evaluation:
                    evaluation.metadata["storage"] = {
                        "cid": upload_result.get("cid", ""),
                        "bucket": self.default_bucket,
                        "storage_time": upload_result.get("timestamp")
                    }
                    
                    # Update task metadata
                    task_metadata["upload_time"] = upload_result.get("timestamp")
                    task_metadata["cid"] = upload_result.get("cid", "")
                    
                return {
                    "success": True,
                    "file_id": task_metadata.get("file_id"),
                    "cid": upload_result.get("cid", ""),
                    "bucket": self.default_bucket,
                    "filename": file_name
                }
                
        except Exception as e:
            logger.error(f"Error in upload phase for task ID {task_id}: {e}")
            
            # Update evaluation with upload failure
            evaluation = await self.evaluator.get_evaluation_status(task_id)
            if evaluation:
                evaluation.metadata["storage_error"] = str(e)
                
            # Return failure result
            return {
                "success": False,
                "error": str(e)
            }

    async def process_reward_phase(
        self,
        task_id: str, 
        user_address: str,
        upload_result: Dict[str, Any],
        task_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process the reward phase of the workflow.
        
        Args:
            task_id: Unique ID for the evaluation task
            user_address: User's wallet address
            upload_result: Result from the upload phase
            task_metadata: Additional metadata about the task
            
        Returns:
            Reward result
        """
        try:
            # Award XP for contribution
            xp_result = await self.reward_service.award_xp(
                user_address, 
                ActivityType.DATASET_CONTRIBUTION
            )
            
            # Update evaluation with reward info
            evaluation = await self.evaluator.get_evaluation_status(task_id)
            if evaluation:
                evaluation.reward = {
                    "xp": xp_result
                }
                
            # Update task metadata
            task_metadata["reward_time"] = xp_result.get("timestamp")
            task_metadata["xp_amount"] = xp_result.get("amount")
            task_metadata["transaction_hash"] = xp_result.get("transaction_hash")
            
            return xp_result
        
        except Exception as e:
            logger.error(f"Error in reward phase for task ID {task_id}: {e}")
            
            # Update evaluation with reward failure
            evaluation = await self.evaluator.get_evaluation_status(task_id)
            if evaluation:
                evaluation.metadata["reward_error"] = str(e)
                
            # Return failure result 
            return {
                "success": False,
                "error": str(e)
            }
            
    async def get_contribution_status(
        self,
        task_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed status information for a contribution
        
        Args:
            task_id: Task ID to check
            
        Returns:
            Status information with phase details
        """
        result = await self.evaluator.get_evaluation_status(task_id)
        
        # Format response
        response = {
            "task_id": task_id,
            "status": result.status,
            "message": result.message,
            "completed": result.completed,
            "phases": {
                "evaluation": {
                    "status": "completed" if result.completed else "processing",
                    "success": result.status in [EvaluationStatus.APPROVED, EvaluationStatus.COMPLETED],
                    "time": result.metadata.get("evaluation_time"),
                    "details": {
                        "blur_score": result.metadata.get("blur_score"),
                        "landmark_score": result.metadata.get("landmark_score")
                    } if "blur_score" in result.metadata else None
                },
                "upload": {
                    "status": "completed" if "storage" in result.metadata else 
                              ("failed" if "storage_error" in result.metadata else "pending"),
                    "success": "storage" in result.metadata,
                    "time": result.metadata.get("storage", {}).get("storage_time") if "storage" in result.metadata else None,
                    "details": result.metadata.get("storage") if "storage" in result.metadata else None,
                    "error": result.metadata.get("storage_error")
                },
                "reward": {
                    "status": "completed" if result.reward else 
                              ("failed" if "reward_error" in result.metadata else "pending"),
                    "success": result.reward is not None,
                    "time": result.metadata.get("reward_time"),
                    "details": result.reward
                }
            }
        }
        
        # Add score if available
        if result.score is not None:
            response["score"] = result.score
            
        return response 