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
        user_address: str,
        client_landmarks=None
    ) -> Dict[str, Any]:
        """
        Submit a contribution for processing
        
        Args:
            file_content: Binary content of the file
            file_name: Original filename
            file_type: MIME type of the file
            user_address: User's wallet address
            client_landmarks: Optional pre-detected hand landmarks from client
            
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
            "reward_time": None,
            "client_landmarks": client_landmarks is not None  # Flag if client landmarks were provided
        }
        
        logger.info(f"Submitted file for evaluation: {file_name}, size: {file_size} bytes")
        if client_landmarks:
            logger.info(f"Client-side landmarks provided for task: {task_id}")
        
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
                "client_landmarks": client_landmarks
            }
        )
        
        return task_metadata
        
    async def process_evaluation_workflow(
        self,
        task_id: str,
        user_address: str,
        file_content: bytes,
        task_metadata: Dict[str, Any],
        client_landmarks=None
    ):
        """
        Orchestrates the three-phase evaluation, upload, and reward workflow.
        
        Args:
            task_id: Unique ID for the evaluation task
            user_address: User's wallet address
            file_content: Binary content of the file
            task_metadata: Additional metadata about the task
            client_landmarks: Optional pre-detected hand landmarks from client
        """
        try:
            logger.info(f"Starting evaluation phase for task ID: {task_id}")
            
            # Phase 1: Evaluate image quality
            evaluation_result = await self.process_evaluation_phase(
                task_id, 
                file_content, 
                task_metadata,
                client_landmarks
            )
            
            # Only proceed if evaluation was approved
            if evaluation_result.status == EvaluationStatus.APPROVED:
                logger.info(f"Evaluation approved for task ID: {task_id}, proceeding to upload phase")
                
                # Update status for frontend polling
                evaluation = await self.evaluator.get_evaluation_status(task_id)
                if evaluation:
                    evaluation.message = "Evaluation approved, uploading to storage..."
                
                # Phase 2: Upload to storage
                upload_result = await self.process_upload_phase(task_id, file_content, task_metadata)
                
                if upload_result.get("success"):
                    logger.info(f"Upload successful for task ID: {task_id}, proceeding to reward phase")
                    
                    # Update status for frontend polling
                    evaluation = await self.evaluator.get_evaluation_status(task_id)
                    if evaluation:
                        evaluation.message = "Upload successful, processing rewards..."
                    
                    # Phase 3: Reward user
                    try:
                        reward_result = await self.process_reward_phase(task_id, user_address, upload_result, task_metadata)
                        
                        # Final status update
                        evaluation = await self.evaluator.get_evaluation_status(task_id)
                        if evaluation:
                            if reward_result.get("success", False):
                                evaluation.message = f"Contribution fully processed. Awarded {reward_result.get('amount', 0)} XP tokens."
                            else:
                                error_msg = reward_result.get("error", "")
                                if "rate limit" in error_msg.lower() or "429" in error_msg:
                                    evaluation.message = "Contribution approved. Rewards delayed due to blockchain rate limits."
                                else:
                                    evaluation.message = "Contribution processed but reward distribution failed."
                    except Exception as reward_error:
                        logger.error(f"Error in reward phase for task ID {task_id}: {reward_error}")
                        
                        # Update evaluation with reward failure but keep the approved status
                        evaluation = await self.evaluator.get_evaluation_status(task_id)
                        if evaluation:
                            error_msg = str(reward_error)
                            if "rate limit" in error_msg.lower() or "429" in error_msg:
                                evaluation.message = "Contribution approved. Rewards delayed due to blockchain rate limits."
                            else:
                                evaluation.message = "Contribution approved but reward distribution failed."
                            evaluation.metadata["reward_error"] = str(reward_error)
                else:
                    logger.error(f"Upload failed for task ID: {task_id}: {upload_result.get('error')}")
                    
                    # Update evaluation with upload failure
                    evaluation = await self.evaluator.get_evaluation_status(task_id)
                    if evaluation:
                        evaluation.status = EvaluationStatus.FAILED
                        evaluation.message = f"Upload failed: {upload_result.get('error')}"
                        evaluation.completed = True
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
        task_metadata: Dict[str, Any],
        client_landmarks=None
    ) -> Any:
        """
        Process the evaluation phase of the workflow.
        
        Args:
            task_id: Unique ID for the evaluation task
            file_content: Binary content of the file
            task_metadata: Additional metadata about the task
            client_landmarks: Optional pre-detected hand landmarks from client
            
        Returns:
            Evaluation result
        """
        try:
            # Create evaluation params
            evaluation_params = {
                "task_id": task_id,
                "file_content": file_content,
            }
            
            # If client landmarks are provided, add them to the evaluation params
            if client_landmarks:
                # Ensure client_landmarks is properly formatted as a list
                if isinstance(client_landmarks, list) and len(client_landmarks) > 0:
                    evaluation_params["landmarks"] = client_landmarks
                    logger.info(f"Using client-provided landmarks for evaluation of task: {task_id}")
                else:
                    logger.warning(f"Client landmarks provided for task {task_id} but format is invalid. Ignoring client landmarks.")
            
            # Run the evaluation
            result = await self.evaluator._process_evaluation(evaluation_params)
            
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
            logger.info(f"Uploading file: {file_name}")
            
            # Upload to storage
            async with self.storage_sdk as client:
                try:
                    upload_result = await client.upload_file(
                        bucket_name=self.default_bucket,
                        file_data=file_content,
                        file_name=file_name
                    )
                    
                    logger.info(f"Uploaded file to storage: {file_name}")
                except Exception as upload_error:
                    # Check if this is a duplicate file error
                    error_str = str(upload_error)
                    if "FileFullyUploaded" in error_str:
                        logger.info(f"File appears to be a duplicate: {file_name}")
                        
                        # Try to extract CID from the error message if possible
                        import json
                        import re
                        
                        # Try to find JSON in the error message
                        json_match = re.search(r'\{.*\}', error_str)
                        cid = None
                        
                        if json_match:
                            try:
                                error_json = json.loads(json_match.group(0))
                                # Some storage providers might include the existing CID in their error
                                if "cid" in error_json:
                                    cid = error_json["cid"]
                            except:
                                pass
                        
                        # If we couldn't extract CID, use a placeholder
                        if not cid:
                            cid = "duplicate-" + task_id
                            
                        # Create a success result with duplicate flag
                        upload_result = {
                            "cid": cid,
                            "timestamp": time.time(),
                            "duplicate": True
                        }
                    else:
                        # Re-raise the original error if it's not a duplicate file error
                        raise

                # Update evaluation metadata with storage details
                evaluation = await self.evaluator.get_evaluation_status(task_id)
                if evaluation:
                    evaluation.metadata["storage"] = {
                        "cid": upload_result.get("cid", ""),
                        "bucket": self.default_bucket,
                        "storage_time": upload_result.get("timestamp"),
                        "duplicate": upload_result.get("duplicate", False)
                    }
                    
                    # Update task metadata
                    task_metadata["upload_time"] = upload_result.get("timestamp")
                    task_metadata["cid"] = upload_result.get("cid", "")
                    task_metadata["duplicate"] = upload_result.get("duplicate", False)
                    
                return {
                    "success": True,
                    "file_id": task_metadata.get("file_id"),
                    "cid": upload_result.get("cid", ""),
                    "bucket": self.default_bucket,
                    "filename": file_name,
                    "duplicate": upload_result.get("duplicate", False)
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
            # Award XP for new contribution through blockchain
            logger.info(f"Awarding XP for task ID: {task_id}")
            try:
                xp_result = self.reward_service.award_xp(
                    user_address, 
                    ActivityType.DATASET_CONTRIBUTION
                )
                
                # Special handling for rate limiting
                if not xp_result.get("success", False) and xp_result.get("is_rate_limited", False):
                    logger.info(f"Blockchain rate limited for task {task_id}, will retry later")
                    # Flag this as rate-limited but still a valid contribution
                    xp_result["rate_limited"] = True
                    xp_result["will_retry"] = True
                    xp_result["fallback"] = True
                    xp_result["message"] = "XP will be awarded automatically when blockchain rate limits clear"
                
            except Exception as reward_error:
                error_str = str(reward_error).lower()
                is_rate_limited = "rate" in error_str or "429" in error_str or "too many requests" in error_str
                
                logger.error(f"Blockchain reward failed for task ID {task_id}: {reward_error}")
                # Fallback to a local reward record if blockchain fails
                xp_result = {
                    "success": False,
                    "amount": 10,
                    "timestamp": time.time(),
                    "fallback": True,
                    "error": str(reward_error),
                    "message": "XP recorded locally due to blockchain error",
                    "is_rate_limited": is_rate_limited
                }
                
                # Add helpful message for rate limiting
                if is_rate_limited:
                    xp_result["message"] = "XP will be awarded automatically when blockchain rate limits clear"
                    xp_result["will_retry"] = True
                    xp_result["rate_limited"] = True
            
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
            task_metadata["is_rate_limited"] = xp_result.get("is_rate_limited", False)
            
            # Return result directly without awaiting it (it's already a dict)
            return xp_result
        
        except Exception as e:
            logger.error(f"Error in reward phase for task ID {task_id}: {e}")
            
            # Update evaluation with reward failure
            evaluation = await self.evaluator.get_evaluation_status(task_id)
            if evaluation:
                error_str = str(e).lower()
                is_rate_limited = "rate" in error_str or "429" in error_str or "too many requests" in error_str
                
                evaluation.metadata["reward_error"] = str(e)
                evaluation.metadata["is_rate_limited"] = is_rate_limited
                
            # Return failure result
            error_str = str(e).lower()
            is_rate_limited = "rate" in error_str or "429" in error_str or "too many requests" in error_str
            
            result = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": time.time(),
                "is_rate_limited": is_rate_limited
            }
            
            if is_rate_limited:
                result["message"] = "XP will be awarded automatically when blockchain rate limits clear"
                result["will_retry"] = True
                
            return result
            
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
        
        # Check if we have a transaction hash but reward status is not complete
        if (result.reward and 
            result.reward.get("xp", {}).get("transaction_hash") and 
            not (result.reward.get("xp", {}).get("success", False))):
            
            tx_hash = result.reward["xp"]["transaction_hash"]
            logger.info(f"Found transaction hash {tx_hash} for task {task_id}, checking status")
            
            # Check transaction status
            try:
                logger.info(f"⭐️ TRANSACTION CHECK: Checking blockchain status for tx {tx_hash}")
                tx_status = self.reward_service.get_transaction_status(tx_hash)
                logger.info(f"⭐️ TRANSACTION STATUS: {tx_status}")
                
                # Update reward status if transaction was successful
                if tx_status.get("status") == "success":
                    logger.info(f"🎉 TRANSACTION CONFIRMED: Updating reward status for task {task_id}")
                    
                    # Update the reward status in the evaluation result
                    result.reward["xp"]["success"] = True
                    result.reward["xp"]["status"] = "completed"
                    result.reward["xp"]["confirmed"] = True
                    result.reward["xp"]["block_number"] = tx_status.get("block_number")
                    result.reward["xp"]["timestamp"] = tx_status.get("timestamp")
                    
                    # Save the updated status
                    await self.evaluator.update_evaluation_status(task_id, result)
                    
                    # Log updated status
                    logger.info(f"✅ REWARD STATUS UPDATED for task {task_id}")
                else:
                    logger.info(f"⏳ TRANSACTION PENDING: Status is {tx_status.get('status')} for tx {tx_hash}")
            except Exception as e:
                logger.error(f"❌ ERROR checking transaction status: {str(e)}")
                # Continue with regular status response even if transaction check fails
        
        # Format response
        response = {
            "task_id": task_id,
            "status": result.status,
            "message": result.message,
            "completed": result.completed,
            "timestamp": time.time(),
            "phases": {
                "evaluation": {
                    "status": "completed" if result.completed else "processing",
                    "success": result.status in [EvaluationStatus.APPROVED, EvaluationStatus.COMPLETED],
                    "time": result.metadata.get("evaluation_time"),
                    "details": {
                        "blur_score": result.metadata.get("blur_score"),
                        "landmark_score": result.metadata.get("landmark_score"),
                        "detected_letter": result.metadata.get("landmark_details", {}).get("letter") if "landmark_details" in result.metadata else None
                    } if "blur_score" in result.metadata else None
                },
                "upload": {
                    "status": "completed" if "storage" in result.metadata else 
                              ("failed" if "storage_error" in result.metadata else "pending"),
                    "success": "storage" in result.metadata,
                    "time": result.metadata.get("storage", {}).get("storage_time") if "storage" in result.metadata else None,
                    "details": {
                        "cid": result.metadata.get("storage", {}).get("cid"),
                        "bucket": result.metadata.get("storage", {}).get("bucket"),
                    } if "storage" in result.metadata else None,
                    "error": result.metadata.get("storage_error")
                },
                "reward": {
                    "status": "completed" if (result.reward and result.reward.get("xp", {}).get("success", False)) else 
                              ("failed" if "reward_error" in result.metadata else "pending"),
                    "success": result.reward is not None and result.reward.get("xp", {}).get("success", False),
                    "time": result.metadata.get("reward_time"),
                    "details": result.reward,
                    "error": result.metadata.get("reward_error")
                }
            }
        }
        
        # Add reward transaction status if available
        if result.reward and result.reward.get("xp", {}).get("transaction_hash"):
            # Include transaction hash in the response for client verification
            tx_hash = result.reward["xp"]["transaction_hash"]
            if "reward" not in response:
                response["reward"] = {}
            if "xp" not in response["reward"]:
                response["reward"]["xp"] = {}
                
            response["reward"]["xp"]["transaction_hash"] = tx_hash
            response["phases"]["reward"]["transaction_hash"] = tx_hash
        
        # Add score if available
        if result.score is not None:
            response["score"] = result.score
            
        return response 
        
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        message: str = None,
        phase: str = None,
        phase_status: str = None,
        phase_success: bool = None,
        phase_details: Dict[str, Any] = None,
        phase_error: str = None
    ) -> Dict[str, Any]:
        """
        Update the status of a task and return the updated status
        
        Args:
            task_id: Task ID to update
            status: New overall status (approved, rejected, etc.)
            message: Optional status message
            phase: Which phase to update (evaluation, upload, reward)
            phase_status: Status of the specific phase
            phase_success: Whether the phase was successful
            phase_details: Additional details for the phase
            phase_error: Error message for the phase
            
        Returns:
            Updated status information
        """
        # Get the current status
        result = await self.evaluator.get_evaluation_status(task_id)
        
        # Update the overall status
        if status:
            result.status = EvaluationStatus(status)
            
        # Update the message
        if message:
            result.message = message
            
        # Update phase-specific information
        if phase:
            # Ensure metadata is initialized
            if not hasattr(result, "metadata"):
                result.metadata = {}
                
            # Update phase-specific status
            if phase == "evaluation":
                # For evaluation phase, update metadata directly
                if phase_status:
                    result.completed = phase_status == "completed"
                if phase_error:
                    result.metadata["evaluation_error"] = phase_error
                    
            elif phase == "upload":
                # For upload phase, update storage information
                if phase_status == "failed":
                    result.metadata["storage_error"] = phase_error
                    
                    # If phase has details, store them
                    if phase_details:
                        if "storage" not in result.metadata:
                            result.metadata["storage"] = {}
                        for key, value in phase_details.items():
                            result.metadata["storage"][key] = value
                elif phase_success:
                    # Only add storage field if successful
                    if "storage" not in result.metadata:
                        result.metadata["storage"] = {}
                    if phase_details:
                        for key, value in phase_details.items():
                            result.metadata["storage"][key] = value
                            
            elif phase == "reward":
                # For reward phase, update reward information
                if phase_error:
                    result.metadata["reward_error"] = phase_error
                    
                # Initialize reward object if needed
                if not result.reward:
                    result.reward = {}
                if "xp" not in result.reward:
                    result.reward["xp"] = {}
                    
                # Update reward status
                result.reward["xp"]["status"] = phase_status
                result.reward["xp"]["success"] = phase_success
                
                # Add details if provided
                if phase_details:
                    for key, value in phase_details.items():
                        result.reward["xp"][key] = value
        
        # Update the stored evaluation
        await self.evaluator.update_evaluation_status(task_id, result)
        
        # Return the updated status
        return await self.get_contribution_status(task_id) 

    async def prepare_reward_transaction(
        self,
        task_id: str, 
        user_address: str,
        task_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepares a reward transaction and returns just the transaction hash without waiting for mining.
        
        Args:
            task_id: Unique ID for the evaluation task
            user_address: User's wallet address
            task_metadata: Additional metadata about the task
            
        Returns:
            Dict with transaction hash and status information
        """
        try:
            # Prepare and submit the transaction
            logger.info(f"Preparing reward transaction for task ID: {task_id}")
            
            # Use the specialized method that just returns the transaction hash
            xp_result = self.reward_service.prepare_award_xp_tx(
                user_address, 
                ActivityType.DATASET_CONTRIBUTION
            )
            
            # Check for rate limiting
            if not xp_result.get("success", False) and xp_result.get("is_rate_limited", False):
                logger.info(f"Blockchain rate limited for task {task_id}, will retry later")
                # Flag this as rate-limited but still provide useful info
                xp_result["rate_limited"] = True
                xp_result["will_retry"] = True
                xp_result["fallback"] = True
                xp_result["message"] = "XP will be awarded automatically when blockchain rate limits clear"
            
            # Update evaluation with transaction hash info
            evaluation = await self.evaluator.get_evaluation_status(task_id)
            if evaluation:
                # Ensure reward object exists
                if not hasattr(evaluation, "reward") or not evaluation.reward:
                    evaluation.reward = {}
                
                # Initialize XP object in reward if needed
                if "xp" not in evaluation.reward:
                    evaluation.reward["xp"] = {}
                
                # Store transaction hash and status in the evaluation
                if xp_result.get("tx_hash") or xp_result.get("transaction_hash"):
                    tx_hash = xp_result.get("tx_hash") or xp_result.get("transaction_hash")
                    evaluation.reward["xp"]["transaction_hash"] = tx_hash
                    evaluation.reward["xp"]["status"] = "processing"
                    
                # Store rate limited status if applicable
                if xp_result.get("is_rate_limited", False):
                    evaluation.reward["xp"]["is_rate_limited"] = True
                    evaluation.reward["xp"]["status"] = "processing"
                    evaluation.reward["xp"]["message"] = "Rate limited, will retry automatically"
                
                # Update metadata 
                evaluation.metadata["reward_started"] = True
                evaluation.metadata["reward_start_time"] = time.time()
                
                if tx_hash:
                    evaluation.metadata["transaction_hash"] = tx_hash
                    
                if xp_result.get("is_rate_limited", False):
                    evaluation.metadata["is_rate_limited"] = True
                
                # Save the updated status
                await self.evaluator.update_evaluation_status(task_id, evaluation)
            
            # Update task metadata
            task_metadata["reward_start_time"] = time.time()
            if xp_result.get("tx_hash") or xp_result.get("transaction_hash"):
                tx_hash = xp_result.get("tx_hash") or xp_result.get("transaction_hash")
                task_metadata["transaction_hash"] = tx_hash
            
            if xp_result.get("is_rate_limited", False):
                task_metadata["is_rate_limited"] = True
            
            # Return the result 
            return xp_result
        
        except Exception as e:
            logger.error(f"Error preparing reward transaction for task ID {task_id}: {e}")
            
            # Check if this is a rate limit error
            error_str = str(e).lower()
            is_rate_limited = "rate" in error_str or "429" in error_str or "too many requests" in error_str
            
            # Update evaluation with error info
            evaluation = await self.evaluator.get_evaluation_status(task_id)
            if evaluation:
                if not hasattr(evaluation, "reward") or not evaluation.reward:
                    evaluation.reward = {}
                if "xp" not in evaluation.reward:
                    evaluation.reward["xp"] = {}
                
                evaluation.reward["xp"]["status"] = "processing" if is_rate_limited else "failed"
                evaluation.metadata["reward_error"] = str(e)
                evaluation.metadata["is_rate_limited"] = is_rate_limited
                
                # Save the updated status
                await self.evaluator.update_evaluation_status(task_id, evaluation)
            
            # Return error result
            result = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": time.time(),
                "is_rate_limited": is_rate_limited
            }
            
            if is_rate_limited:
                result["message"] = "XP will be awarded automatically when blockchain rate limits clear"
                result["will_retry"] = True
                
            return result 