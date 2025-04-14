from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form, Body, Depends
from typing import Dict, Any, Optional, List
from ...services.storage.akave_sdk import AkaveError
from ...services.service_container import get_contribution_service, get_storage_sdk, initialize_services
from ...core.config import settings
from ...services.evaluator import EvaluationStatus
import logging
import traceback
import json
import time
from fastapi.responses import StreamingResponse
import asyncio
import hashlib
from ...schemas.Storage import RewardRequest
import uuid
import re

# Initialize all services
initialize_services()

router = APIRouter(prefix="/storage", tags=["storage"])
logger = logging.getLogger(__name__)

# In-memory store of job statuses for the example
LILYPAD_JOBS = {}

@router.post("/contribution")
async def upload_file(
    file: UploadFile = File(...),
    user_address: str = Form(...),
    landmarks: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> Dict[str, Any]:
    """
    Handle file upload with a three-phase process:
    1. Evaluate image quality
    2. Upload approved images
    3. Reward users for approved contributions
    
    If landmarks are provided from client-side detection, skip landmark detection step.
    """
    # First check if the file is valid
    if not file or not file.filename:
        logger.error("Missing file or filename in upload request")
        return {
            "success": False,
            "error": "No file provided or filename is missing"
        }
        
    # Extract file information for logging/debugging
    file_size = getattr(file, "size", None)
    if file_size is None:
        # Estimate file size if not provided in metadata
        try:
            position = await file.seek(0, 2)  # Seek to end
            file_size = position
            await file.seek(0)  # Reset position for reading
        except Exception as e:
            logger.warning(f"Could not determine file size: {e}")
            file_size = "unknown"
    
    logger.info(f"Processing contribution: {file.filename}, size: {file_size}, type: {file.content_type}")
    
    # Validate wallet address
    if not user_address:
        logger.error("User address missing in contribution upload")
        return {
            "success": False,
            "error": "User address is required for rewards"
        }
    
    logger.info(f"Processing contribution from address: {user_address}")
    
    # Process landmarks if provided from client-side detection
    client_landmarks = None
    if landmarks:
        try:
            client_landmarks = json.loads(landmarks)
            logger.info(f"Received client-side landmarks with {len(client_landmarks) // 3} points")
        except Exception as e:
            logger.warning(f"Failed to parse client landmarks: {e}")
            # Continue without landmarks rather than failing
    
    # Get contribution service from container    
    contribution_service = get_contribution_service()
    
    try:
        # 1. Read file content
        try:
            file_content = await file.read()
            logger.info(f"Read {len(file_content)} bytes from file {file.filename}")
        except Exception as read_error:
            logger.error(f"Failed to read file content: {read_error}")
            return {
                "success": False,
                "error": f"Failed to read file content: {str(read_error)}"
            }
        
        # Check if file is actually an image
        if not file.content_type.startswith('image/'):
            logger.error(f"Invalid file type: {file.content_type}")
            return {
                "success": False,
                "error": "Only image files are supported"
            }

        # 2. Submit contribution to get task ID
        try:
            task_metadata = await contribution_service.submit_contribution(
                file_content=file_content,
                file_name=file.filename,
                file_type=file.content_type,
                user_address=user_address,
                client_landmarks=client_landmarks
            )
            
            # Extract task ID for tracking
            task_id = task_metadata.get("task_id")
            if not task_id:
                logger.error("No task ID returned from contribution submission")
                return {
                    "success": False,
                    "error": "Failed to create evaluation task"
                }
                
            logger.info(f"Created evaluation task ID: {task_id}")
        except Exception as submit_error:
            # Check specifically for duplicate file indications
            if "duplicate" in str(submit_error).lower() or "already uploaded" in str(submit_error).lower():
                logger.info(f"Duplicate file detected: {file.filename}")
                return {
                    "success": False,
                    "error": "This file has already been uploaded. Please try a different image.",
                    "duplicate": True,
                    "message": "Duplicate file detected. Please try a different image."
                }
            
            logger.error(f"Failed to submit contribution: {submit_error}")
            return {
                "success": False,
                "error": f"Failed to submit contribution: {str(submit_error)}"
            }
        
    except Exception as e:
        error_stack = traceback.format_exc()
        logger.error(f"Contribution upload error: {str(e)}")
        logger.error(error_stack)
        
        # Check if it's a duplicate file error that was not caught by the lower-level code
        if "FileFullyUploaded" in str(e) or "duplicate" in str(e).lower():
            logger.info(f"Duplicate file detected for {file.filename}")
            return {
                "success": False,
                "error": "This file has already been uploaded. Please try a different image.",
                "duplicate": True,
                "message": "Duplicate file detected. Please try a different image."
            }
            
        # Return detailed error information
        return {
            "success": False,
            "error": f"Upload failed: {str(e)}",
            "details": {
                "error_type": type(e).__name__,
                "file_name": file.filename if file else "unknown",
                "file_type": file.content_type if file else "unknown",
                "user_address": user_address
            }
        }

@router.get("/contribution/status/{task_id}")
async def get_evaluation_status(
    task_id: str, 
    tx_hash: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get the status of an evaluation task with detailed phase information
    
    Arguments:
        task_id: The task ID to get status for
        tx_hash: Optional transaction hash to directly check blockchain status
    """
    try:
        logger.info(f"Fetching evaluation status for task: {task_id}")
        
        # Get status from contribution service
        contribution_service = get_contribution_service()
        status = await contribution_service.get_contribution_status(task_id)
        
        # If tx_hash is provided, check transaction status directly
        if tx_hash:
            logger.info(f"Checking transaction status for hash: {tx_hash}")
            try:
                # Get transaction status from reward service
                tx_status = contribution_service.reward_service.get_transaction_status(tx_hash)
                
                logger.info(f"Transaction status for {tx_hash}: {tx_status.get('status')}")
                
                # Add transaction status to response
                if "reward" not in status:
                    status["reward"] = {}
                if "xp" not in status["reward"]:
                    status["reward"]["xp"] = {}
                
                # Include transaction status in the response
                status["transaction_status"] = tx_status
                
                # If transaction is confirmed successful, update reward status
                if tx_status.get("status") == "success":
                    logger.info(f"Transaction {tx_hash} confirmed successful")
                    
                    # Update reward phase status
                    if "phases" in status and "reward" in status["phases"]:
                        status["phases"]["reward"]["status"] = "completed"
                        status["phases"]["reward"]["success"] = True
                        if "details" not in status["phases"]["reward"]:
                            status["phases"]["reward"]["details"] = {}
                        status["phases"]["reward"]["details"]["transaction_status"] = tx_status.get("status")
                        status["phases"]["reward"]["details"]["block_number"] = tx_status.get("block_number")
                        status["phases"]["reward"]["details"]["transaction_hash"] = tx_hash
                    
                    # Also update reward object if it exists
                    if "reward" in status and "xp" in status["reward"]:
                        status["reward"]["xp"]["status"] = "completed"
                        status["reward"]["xp"]["success"] = True
                        status["reward"]["xp"]["transaction_hash"] = tx_hash
                        status["reward"]["xp"]["block_number"] = tx_status.get("block_number")
                        status["reward"]["xp"]["transaction_status"] = tx_status.get("status")
                        
                    # Update evaluation record in database with this status
                    # This is important so future calls without tx_hash will show correct status
                    evaluation = await contribution_service.evaluator.get_evaluation_status(task_id)
                    if evaluation:
                        if not evaluation.reward:
                            evaluation.reward = {}
                        if "xp" not in evaluation.reward:
                            evaluation.reward["xp"] = {}
                            
                        evaluation.reward["xp"]["success"] = True
                        evaluation.reward["xp"]["status"] = "completed"
                        evaluation.reward["xp"]["transaction_hash"] = tx_hash
                        evaluation.reward["xp"]["block_number"] = tx_status.get("block_number")
                        
                        await contribution_service.evaluator.update_evaluation_status(task_id, evaluation)
                        logger.info(f"Updated evaluation record with successful transaction status for {task_id}")
                
                # If transaction failed, update status accordingly
                elif tx_status.get("status") == "failed":
                    logger.info(f"Transaction {tx_hash} failed")
                    
                    # Update reward phase status to show transaction failed
                    if "phases" in status and "reward" in status["phases"]:
                        status["phases"]["reward"]["status"] = "failed"
                        status["phases"]["reward"]["success"] = False
                        status["phases"]["reward"]["error"] = "Transaction failed on blockchain"
                        if "details" not in status["phases"]["reward"]:
                            status["phases"]["reward"]["details"] = {}
                        status["phases"]["reward"]["details"]["transaction_status"] = tx_status.get("status")
                        status["phases"]["reward"]["details"]["block_number"] = tx_status.get("block_number")
                        status["phases"]["reward"]["details"]["transaction_hash"] = tx_hash
                        status["phases"]["reward"]["details"]["error"] = tx_status.get("error")
                
                # For pending transactions, ensure status reflects this
                elif tx_status.get("status") == "pending":
                    if "phases" in status and "reward" in status["phases"]:
                        status["phases"]["reward"]["status"] = "processing"
                        if "details" not in status["phases"]["reward"]:
                            status["phases"]["reward"]["details"] = {}
                        status["phases"]["reward"]["details"]["transaction_status"] = "pending"
                        status["phases"]["reward"]["details"]["transaction_hash"] = tx_hash
            
            except Exception as tx_error:
                logger.error(f"Error checking transaction status: {str(tx_error)}")
                # Add error info but don't fail the whole request
                status["transaction_status_error"] = str(tx_error)
        
        logger.info(f"Status for task {task_id}: {status['status']}, completed: {status['completed']}")
        return status
        
    except Exception as e:
        error_stack = traceback.format_exc()
        logger.error(f"Error getting evaluation status: {str(e)}")
        logger.error(error_stack)
        
        return {
            "success": False,
            "error": f"Failed to get evaluation status: {str(e)}"
        }

@router.get('/files')
async def list_files() -> Dict[str, Any]:
    """List all files"""
    try:
        logger.info("Listing files")
        akave_sdk = get_storage_sdk()
        async with akave_sdk as client:
            files = await client.list_files("asl-training-data")
            return {"success": True, "files": files}
    except Exception as e:
        error_stack = traceback.format_exc()
        logger.error(f"Failed to list files: {str(e)}")
        logger.error(error_stack)
        
        return {
            "success": False,
            "error": f"Failed to list files: {str(e)}"
        }

@router.post('/upload')
async def upload_file_direct(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload a file directly to Akave storage.
    Supports binary files (images, videos, etc.)
    """
    try:
        # Read file as bytes
        contents = await file.read()
        file_size = len(contents)

        logger.info(f"Processing direct upload: {file.filename}, size: {file_size} bytes")
        
        akave_sdk = get_storage_sdk()
        async with akave_sdk as client:
            result = await client.upload_file(
                bucket_name="asl-training-data",
                file_data=contents,
                file_name=file.filename
            )

            return {
                "success": True,
                "message": "File uploaded successfully",
                "filename": file.filename,
                "size": file_size,
                "cid": result.get("cid", ""),
                "bucket": "asl-training-data",
                "contentType": file.content_type
            }

    except AkaveError as e:
        error_stack = traceback.format_exc()
        logger.error(f"Akave storage error: {str(e)}")
        logger.error(error_stack)
        
        return {
            "success": False,
            "error": f"Storage error: {str(e)}"
        }
    except Exception as e:
        error_stack = traceback.format_exc()
        logger.error(f"Upload error: {str(e)}")
        logger.error(error_stack)
        
        return {
            "success": False,
            "error": f"Upload failed: {str(e)}"
        }

@router.post('/diagnostic')
async def upload_diagnostic(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Diagnostic endpoint to test file upload functionality.
    This helps debug file-related issues without going through the entire pipeline.
    """
    try:
        # Read file as bytes
        contents = await file.read()
        file_size = len(contents)
        file_summary = contents[:100].hex() if contents else "empty"

        logger.info(f"Diagnostic file upload: {file.filename}, size: {file_size} bytes")
        
        # Return diagnostic information
        return {
            "success": True,
            "message": "Diagnostic file upload successful",
            "filename": file.filename,
            "size": file_size,
            "content_type": file.content_type,
            "content_summary": file_summary,
            "headers": dict(file.headers) if hasattr(file, 'headers') else {},
            "timestamp": time.time()
        }

    except Exception as e:
        error_stack = traceback.format_exc()
        logger.error(f"Diagnostic upload error: {str(e)}")
        logger.error(error_stack)
        
        return {
            "success": False,
            "error": f"Diagnostic upload failed: {str(e)}",
            "error_type": type(e).__name__,
            "error_details": str(e)
        }

@router.get("/evaluation/status/stream/{task_id}")
async def get_evaluation_status_stream(
    task_id: str,
    tx_hash: Optional[str] = None
) -> StreamingResponse:
    """
    Get the status of an evaluation task using Server-Sent Events
    
    Arguments:
        task_id: The task ID to get status for
        tx_hash: Optional transaction hash to directly check blockchain status
    """
    async def generate_status_stream():
        contribution_service = get_contribution_service()
        while True:
            try:
                # Use the same endpoint as the regular status check
                status = await get_evaluation_status(task_id, tx_hash)
                yield f"data: {json.dumps(status)}\n\n"
            except Exception as e:
                logger.error(f"Error in status stream: {str(e)}")
                # Return error as event data
                yield f"data: {json.dumps({'error': str(e), 'task_id': task_id})}\n\n"
                
            await asyncio.sleep(2)  # Slightly longer interval for streaming to reduce load

    return StreamingResponse(generate_status_stream(), media_type="text/event-stream")

@router.post("/evaluate")
async def evaluate_contribution(
    file: UploadFile = File(...),
    user_address: str = Form(...),
    landmarks: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """
    Phase 1: Evaluate a contribution to check quality and hand detection
    
    Arguments:
        file: The image file to evaluate
        user_address: User's wallet address
        landmarks: Optional pre-detected hand landmarks from client
        
    Returns:
        Evaluation result with task_id for further operations
    """
    # First check if the file is valid
    if not file or not file.filename:
        logger.error("Missing file or filename in evaluation request")
        return {
            "success": False,
            "error": "No file provided or filename is missing"
        }
    
    # Validate wallet address
    if not user_address:
        logger.error("User address missing in contribution evaluation")
        return {
            "success": False,
            "error": "User address is required"
        }
    
    # Process landmarks if provided from client-side detection
    client_landmarks = None
    if landmarks:
        try:
            client_landmarks = json.loads(landmarks)
            logger.info(f"Received client-side landmarks with {len(client_landmarks) // 3} points")
        except Exception as e:
            logger.warning(f"Failed to parse client landmarks: {e}")
    
    try:
        # Read file content
        try:
            file_content = await file.read()
            file_size = len(file_content)
            logger.info(f"Read {file_size} bytes from file {file.filename}")
        except Exception as read_error:
            logger.error(f"Failed to read file content: {read_error}")
            return {
                "success": False,
                "error": f"Failed to read file content: {str(read_error)}"
            }
        
        # Get contribution service
        contribution_service = get_contribution_service()
        
        # Submit contribution to get task ID
        try:
            task_metadata = await contribution_service.submit_contribution(
                file_content=file_content,
                file_name=file.filename,
                file_type=file.content_type,
                user_address=user_address,
                client_landmarks=client_landmarks
            )
            
            # Extract task ID for tracking
            task_id = task_metadata.get("task_id")
            if not task_id:
                logger.error("No task ID returned from contribution submission")
                return {
                    "success": False,
                    "error": "Failed to create evaluation task"
                }
                
            logger.info(f"Created evaluation task ID: {task_id}")
            
            # Process only the evaluation phase
            evaluation_result = await contribution_service.process_evaluation_phase(
                task_id=task_id,
                file_content=file_content,
                task_metadata=task_metadata,
                client_landmarks=client_landmarks
            )
            
            # Get status for response
            evaluation_status = await contribution_service.get_contribution_status(task_id)
            
            # Return result with task_id and file_content hash for verification
            content_hash = hashlib.md5(file_content).hexdigest()
            
            return {
                "success": True,
                "task_id": task_id,
                "message": "Contribution evaluated successfully",
                "status": evaluation_status["status"],
                "content_hash": content_hash,
                "file_info": {
                    "filename": file.filename,
                    "size": file_size,
                    "type": file.content_type
                },
                "evaluation": evaluation_status["phases"]["evaluation"]
            }
            
        except Exception as submit_error:
            logger.error(f"Failed to evaluate contribution: {submit_error}")
            return {
                "success": False,
                "error": f"Evaluation failed: {str(submit_error)}"
            }
            
    except Exception as e:
        error_stack = traceback.format_exc()
        logger.error(f"Contribution evaluation error: {str(e)}")
        logger.error(error_stack)
        
        return {
            "success": False,
            "error": f"Evaluation failed: {str(e)}",
            "details": {
                "error_type": type(e).__name__,
                "file_name": file.filename if file else "unknown",
                "file_type": file.content_type if file else "unknown",
                "user_address": user_address
            }
        }

@router.post("/upload/{task_id}")
async def upload_contribution(
    task_id: str,
    file: UploadFile = File(...),
    content_hash: str = Form(...),
    user_address: str = Form(...)
) -> Dict[str, Any]:
    """
    Phase 2: Upload a contribution to permanent storage after it's been evaluated
    
    Arguments:
        task_id: The task ID from the evaluation phase
        file: The image file to upload
        content_hash: MD5 hash of the file content to verify it's the same file that was evaluated
        user_address: User's wallet address
        
    Returns:
        Upload result with storage details
    """
    try:
        # Read file content
        file_content = await file.read()
        
        # Verify content hash
        actual_hash = hashlib.md5(file_content).hexdigest()
        if actual_hash != content_hash:
            logger.error(f"Content hash mismatch: expected {content_hash}, got {actual_hash}")
            return {
                "success": False,
                "error": "File content has changed since evaluation",
                "details": {
                    "expected_hash": content_hash,
                    "actual_hash": actual_hash
                }
            }
        
        # Get contribution service
        contribution_service = get_contribution_service()
        
        # Get existing task metadata
        status = await contribution_service.get_contribution_status(task_id)
        if not status or status.get("status") == "pending":
            logger.error(f"No evaluation found for task ID: {task_id}")
            return {
                "success": False,
                "error": "This file has not been evaluated yet. Please evaluate first."
            }
        
        # Only proceed if evaluation was approved
        if status.get("status") != "approved":
            logger.error(f"Evaluation was not approved for task ID: {task_id}")
            return {
                "success": False,
                "error": "Evaluation was not approved. Cannot upload file.",
                "evaluation_status": status.get("status")
            }
        
        # Create task metadata from existing data
        task_metadata = {
            "task_id": task_id,
            "file_id": status.get("phases", {}).get("evaluation", {}).get("details", {}).get("file_id"),
            "filename": file.filename,
            "file_size": len(file_content),
            "content_type": file.content_type,
            "user_address": user_address
        }
        
        # Process upload phase
        upload_result = await contribution_service.process_upload_phase(
            task_id=task_id,
            file_content=file_content,
            task_metadata=task_metadata
        )
        
        # Check if this is a duplicate file
        if not upload_result.get("success") and upload_result.get("duplicate"):
            logger.info(f"Duplicate file detected during upload for task ID: {task_id}")
            # Update task status to indicate rejection due to duplicate
            await contribution_service.update_task_status(
                task_id=task_id,
                status="rejected",
                message="Duplicate file detected. Please try a different image.",
                phase="upload",
                phase_status="failed",
                phase_success=False,
                phase_details={"duplicate": True},
                phase_error="This file has already been uploaded."
            )
            
            return {
                "success": False,
                "error": "This file has already been uploaded. Please try a different image.",
                "duplicate": True,
                "message": "Duplicate file detected. Please try a different image.",
                "status": "rejected"
            }
        
        # Check if storage details indicate a duplicate (some storage providers may return success but mark as duplicate)
        if upload_result.get("success") and upload_result.get("duplicate"):
            logger.info(f"Storage reported successful upload but marked as duplicate for task ID: {task_id}")
            # Update task status to indicate rejection due to duplicate
            await contribution_service.update_task_status(
                task_id=task_id,
                status="rejected",
                message="Duplicate file detected. Please try a different image.",
                phase="upload",
                phase_status="failed",
                phase_success=False,
                phase_details={"duplicate": True, "cid": upload_result.get("cid"), "bucket": upload_result.get("bucket")},
                phase_error="This file has already been uploaded."
            )
            
            return {
                "success": False,
                "error": "This file has already been uploaded. Please try a different image.",
                "duplicate": True,
                "message": "Duplicate file detected. Please try a different image.",
                "status": "rejected"
            }
        
        # If upload failed for other reasons
        if not upload_result.get("success"):
            logger.error(f"Upload failed for task ID: {task_id}: {upload_result.get('error')}")
            return {
                "success": False,
                "error": f"Upload failed: {upload_result.get('error')}"
            }
        
        # Get updated status
        status = await contribution_service.get_contribution_status(task_id)
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Contribution uploaded successfully",
            "status": status["status"],
            "upload": status["phases"]["upload"],
            "storage": {
                "cid": upload_result.get("cid"),
                "bucket": upload_result.get("bucket"),
                "duplicate": False  # Explicitly set to false since we've handled duplicates above
            }
        }
        
    except Exception as e:
        error_stack = traceback.format_exc()
        logger.error(f"Contribution upload error: {str(e)}")
        logger.error(error_stack)
        
        # Check if it's a duplicate file error
        if "FileFullyUploaded" in str(e) or "duplicate" in str(e).lower():
            logger.info(f"Duplicate file detected for task ID: {task_id}")
            # Update task status to indicate rejection due to duplicate
            try:
                contribution_service = get_contribution_service()
                await contribution_service.update_task_status(
                    task_id=task_id,
                    status="rejected",
                    message="Duplicate file detected. Please try a different image.",
                    phase="upload",
                    phase_status="failed",
                    phase_success=False,
                    phase_details={"duplicate": True},
                    phase_error="This file has already been uploaded."
                )
            except Exception as update_error:
                logger.error(f"Failed to update task status: {update_error}")
            
            return {
                "success": False,
                "error": "This file has already been uploaded. Please try a different image.",
                "duplicate": True,
                "message": "Duplicate file detected. Please try a different image.",
                "status": "rejected"
            }
        
        return {
            "success": False,
            "error": f"Upload failed: {str(e)}",
            "details": {
                "error_type": type(e).__name__,
                "task_id": task_id,
                "file_name": file.filename
            }
        }

@router.post("/reward/{task_id}")
async def process_reward(
    task_id: str,
    payload: RewardRequest,
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> Dict[str, Any]:
    """
    Phase 3: Process rewards for a contribution after it's been evaluated and uploaded
    
    Arguments:
        task_id: The task ID from previous phases
        payload: JSON body with address fields (primary source) {
            "user_address": str
        }
        
    Returns:
        Reward result with blockchain transaction details
    """
    try:
        # Get contribution service
        user_address = payload.user_address
        contribution_service = get_contribution_service()
        
        logger.info(f"Processing reward request for task {task_id}")
        logger.info(f"Using address {user_address} for rewards processing")
        
        # Get existing task status
        status = await contribution_service.get_contribution_status(task_id)
        if not status or status.get("status") == "pending":
            logger.error(f"No evaluation found for task ID: {task_id}")
            return {
                "success": False,
                "error": "This file has not been processed yet. Please evaluate and upload first."
            }
        
        # Check for duplicate files and reject reward processing immediately
        is_duplicate = status.get("phases", {}).get("upload", {}).get("details", {}).get("duplicate", False)
        if is_duplicate or status.get("status") == "rejected":
            logger.info(f"Rejecting reward for duplicate file, task ID: {task_id}")
            return {
                "success": False,
                "error": "Duplicate files are not eligible for rewards",
                "message": "This file appears to be a duplicate. No rewards will be processed.",
                "status": "rejected",
                "duplicate": True,
                "phases": {
                    "evaluation": status["phases"]["evaluation"],
                    "upload": status["phases"]["upload"],
                    "reward": {
                        "status": "failed",
                        "success": False,
                        "error": "Duplicate files are not eligible for rewards",
                        "details": {"duplicate": True}
                    }
                }
            }
        
        # Verify the upload phase was completed
        upload_phase = status.get("phases", {}).get("upload", {})
        if upload_phase.get("status") != "completed" or not upload_phase.get("success"):
            logger.error(f"Upload phase not completed for task ID: {task_id}")
            return {
                "success": False,
                "error": "Upload phase not completed. Cannot process rewards.",
                "upload_status": upload_phase.get("status")
            }
        
        # Create task metadata from existing data
        task_metadata = {
            "task_id": task_id,
            "file_id": status.get("phases", {}).get("evaluation", {}).get("details", {}).get("file_id"),
            "user_address": user_address
        }
        
        logger.info(f"Starting reward processing for task {task_id} with address {user_address}")
        
        # Use the new method to just get the transaction hash quickly
        tx_result = await contribution_service.prepare_reward_transaction(
            task_id=task_id,
            user_address=user_address,
            task_metadata=task_metadata
        )
        
        # Get the transaction hash if available
        tx_hash = tx_result.get("tx_hash") or tx_result.get("transaction_hash")
        is_rate_limited = tx_result.get("is_rate_limited", False)
        
        # Return a response with the transaction hash
        if tx_hash:
            return {
                "success": True,
                "task_id": task_id,
                "message": "Reward transaction submitted",
                "status": status["status"],
                "transaction_hash": tx_hash,
                "phases": {
                    "evaluation": status["phases"]["evaluation"],
                    "upload": status["phases"]["upload"],
                    "reward": {
                        "status": "processing",
                        "success": False,
                        "message": "Reward transaction submitted",
                        "details": {
                            "transaction_hash": tx_hash
                        }
                    }
                }
            }
        elif is_rate_limited:
            return {
                "success": True,
                "task_id": task_id,
                "message": "Reward processing delayed due to blockchain rate limits",
                "status": status["status"],
                "is_rate_limited": True,
                "phases": {
                    "evaluation": status["phases"]["evaluation"],
                    "upload": status["phases"]["upload"],
                    "reward": {
                        "status": "processing",
                        "success": False,
                        "message": "Blockchain rate limited. Will retry automatically.",
                        "is_rate_limited": True,
                        "details": {
                            "is_rate_limited": True
                        }
                    }
                }
            }
        else:
            return {
                "success": True,
                "task_id": task_id,
                "message": "Reward processing started in background",
                "status": status["status"],
                "phases": {
                    "evaluation": status["phases"]["evaluation"],
                    "upload": status["phases"]["upload"],
                    "reward": {
                        "status": "processing",
                        "success": False,
                        "message": "Reward processing started in background"
                    }
                }
            }
    except Exception as e:
        error_stack = traceback.format_exc()
        logger.error(f"Reward processing error: {str(e)}")
        logger.error(error_stack)
        
        return {
            "success": False,
            "error": f"Reward processing failed: {str(e)}",
            "details": {
                "error_type": type(e).__name__,
            }
        }

@router.post("/evaluate_lilypad")
async def evaluate_landmarks_lilypad(
    file: UploadFile = File(...),
    user_address: str = Form(...),
    landmarks: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> Dict[str, Any]:
    """
    Evaluate sign language using the Lilypad module
    This runs as a background task and returns a job ID for status polling
    """
    
    try:
        # Create a unique job ID
        job_id = str(uuid.uuid4())
        LILYPAD_JOBS[job_id] = {"status": "pending", "result": None}
        
        logger.info(f"Starting Lilypad evaluation job {job_id} for user {user_address}")
        
        # Process landmarks if provided
        if not landmarks:
            return {
                "success": False,
                "error": "Landmarks are required for Lilypad evaluation",
                "job_id": job_id,
                "status": "failed"
            }
            
        # Read file content for blur detection
        file_content = await file.read()
        
        # Calculate content hash for file verification
        content_hash = hashlib.md5(file_content).hexdigest()
        
        # Get contribution service
        contribution_service = get_contribution_service()
        
        # Create initial task metadata
        task_metadata = {
            "task_id": job_id,
            "file_id": job_id,  # Use job_id as file_id for tracking
            "filename": file.filename,
            "file_size": len(file_content),
            "content_type": file.content_type,
            "user_address": user_address,
            "content_hash": content_hash  # Store hash in metadata
        }
        
        # Perform blur detection only using the evaluation phase
        blur_result = await contribution_service.process_evaluation_phase(
            task_id=job_id,
            file_content=file_content,
            task_metadata=task_metadata,
            client_landmarks=json.loads(landmarks),
            blur_only=True  # New parameter to only do blur detection
        )
        
        # Check if image is too blurry - EvaluationResult is a Pydantic model, not a dict
        if blur_result.status == EvaluationStatus.REJECTED or not blur_result.completed:
            # If blurry, return immediately with failure but still include job_id for tracking
            LILYPAD_JOBS[job_id]["status"] = "failed"
            LILYPAD_JOBS[job_id]["result"] = {
                "status": "error",
                "message": "Image is too blurry",
                "blur_score": blur_result.metadata.get("blur_score", 0)
            }
            
            return {
                "success": False,
                "error": "Image is too blurry. Please try with a clearer image.",
                "job_id": job_id,
                "status": "failed",
                "task_id": job_id,  # Include task_id for frontend tracking
                "blur_score": blur_result.metadata.get("blur_score", 0),
                "evaluation": {
                    "status": "failed",
                    "success": False,
                    "details": {
                        "blur_score": blur_result.metadata.get("blur_score", 0)
                    }
                }
            }
            
        # File position needs to be reset after reading
        await file.seek(0)
        
        # Parse landmarks
        try:
            landmarks_data = json.loads(landmarks)
            logger.info(f"Parsed landmarks with {len(landmarks_data)} points")
        except Exception as e:
            logger.error(f"Failed to parse landmarks data: {e}")
            LILYPAD_JOBS[job_id]["status"] = "failed"
            LILYPAD_JOBS[job_id]["result"] = {
                "status": "error",
                "message": f"Invalid landmarks format: {str(e)}"
            }
            return {
                "success": False,
                "error": f"Invalid landmarks format: {str(e)}",
                "job_id": job_id,
                "task_id": job_id,
                "status": "failed"
            }
        
        # Add the background task for Lilypad processing
        background_tasks.add_task(
            run_lilypad_evaluation,
            landmarks_data,
            job_id
        )
        
        # Return success with evaluation details including blur score
        return {
            "success": True,
            "job_id": job_id,
            "task_id": job_id,  # Include task_id for frontend tracking
            "status": "processing",
            "message": "Lilypad evaluation started",
            "content_hash": content_hash,  # Include content hash for upload phase
            "evaluation": {
                "status": "completed",
                "success": True,
                "details": {
                    "blur_score": blur_result.metadata.get("blur_score", 0.8),  # Include blur score from detection
                    "landmark_score": blur_result.metadata.get("landmark_score", 0.9)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Lilypad evaluation error: {str(e)}")
        
        # If job_id was created, update its status
        if 'job_id' in locals():
            LILYPAD_JOBS[job_id]["status"] = "failed"
            LILYPAD_JOBS[job_id]["result"] = {
                "status": "error",
                "message": str(e)
            }
            
            return {
                "success": False,
                "error": f"Lilypad evaluation failed: {str(e)}",
                "job_id": job_id,
                "task_id": job_id,
                "status": "failed"
            }
        
        return {
            "success": False,
            "error": f"Lilypad evaluation failed: {str(e)}",
            "status": "failed"
        }

async def run_lilypad_evaluation(landmarks_data: list[float], job_id: str):
    """Background task to run the Lilypad evaluation"""
    
    import subprocess
    import os
    
    try:
        # Convert landmarks to properly formatted JSON
        env_vars = os.environ.copy()
        logger.info(f"Landmarks data: {landmarks_data}")
        logger.info(f"Landmarks data type: {type(landmarks_data)}")
        
        # Properly format landmarks as JSON and escape it for command-line use
        landmarks_json = json.dumps(landmarks_data)
        
        # Prepare the lilypad command
        env_vars["WEB3_PRIVATE_KEY"] = settings.WEB3_PRIVATE_KEY

        command = [
            "lilypad",
            "run",
            "github.com/ce20480/lilypad-module-sl:d1792d4fd72577718c1c4318892b262076d9ff66",
            "-i",
            f'INPUT={landmarks_json}'
        ]
        
        logger.info(f"Running Lilypad command for job {job_id}")
        logger.info(f"Command: {' '.join(command)}")
        
        # Run the Lilypad module in a subprocess
        result = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True,
            env=env_vars
        )
        if result.stderr:
            logger.error(f"Lilypad subprocess error for job {job_id}: {result.stderr}")
            LILYPAD_JOBS[job_id]["status"] = "error"
            LILYPAD_JOBS[job_id]["result"] = {
                "status": "error",
                "message": result.stderr
            }
        
        # Log subprocess output for debugging
        logger.info(f"Command stdout: {result.stdout[:500]}...")
        if result.stderr:
            logger.warning(f"Command stderr: {result.stderr}")
        
        # Parse the output to find the file path
        lines = result.stdout.strip().split("\n")
        path_line = None
        
        # Search from the bottom up for the output file path
        for line in reversed(lines):
            line_stripped = line.strip()
            if "open /tmp/lilypad/data/downloaded-files" in line_stripped:
                path_line = line_stripped
                break
        
        if not path_line:
            # No matching line found - try regex search
            pattern = r"open\s+(/tmp/lilypad/data/downloaded-files/\S+)"
            match = re.search(pattern, result.stdout)
            if match:
                dir_path = match.group(1)
                file_path = os.path.join(dir_path, "outputs", "result.json")
            else:
                # Handle error - no output path found
                logger.error(f"Could not find output path in Lilypad response for job {job_id}")
                LILYPAD_JOBS[job_id]["status"] = "error"
                LILYPAD_JOBS[job_id]["result"] = {
                    "status": "error",
                    "message": "Could not find output path in Lilypad response"
                }
                return
        else:
            # Parse the path line
            path_line = path_line.replace("open ", "")
            file_path = os.path.join(path_line, "outputs", "result.json")
        
        logger.info(f"Looking for result file at: {file_path}")
        if not os.path.exists(file_path):
            # If the file doesn't exist, handle the error
            logger.error(f"Result file not found at {file_path} for job {job_id}")
            LILYPAD_JOBS[job_id]["status"] = "error"
            LILYPAD_JOBS[job_id]["result"] = {
                "status": "error",
                "message": f"Could not find result.json at {file_path}"
            }
            return
        
        # Read and parse the result.json
        with open(file_path, "r") as f:
            file_data = json.load(f)
        
        logger.info(f"Loaded result data: {file_data}")
        
        # Check for errors in the output field (Lilypad model format)
        if "output" in file_data and file_data["output"].get("status") == "error":
            # Extract error message from output
            error_message = file_data["output"].get("message", "Unknown model error")
            logger.error(f"Lilypad module returned error for job {job_id}: {error_message}")
            LILYPAD_JOBS[job_id]["status"] = "error"
            LILYPAD_JOBS[job_id]["result"] = file_data
        elif file_data.get("status") == "error":
            # Legacy format - direct error in the root object
            logger.error(f"Lilypad module returned error for job {job_id}: {file_data.get('message', 'Unknown error')}")
            LILYPAD_JOBS[job_id]["status"] = "error"
            LILYPAD_JOBS[job_id]["result"] = file_data
        else:
            # Success case
            logger.info(f"Lilypad evaluation completed successfully for job {job_id}")
            LILYPAD_JOBS[job_id]["status"] = "completed"
            LILYPAD_JOBS[job_id]["result"] = file_data
    
    except subprocess.CalledProcessError as e:
        # Handle subprocess error
        logger.error(f"Lilypad subprocess error for job {job_id}: {e}")
        # logger.error(f"Stderr: {e.stderr}")
        # logger.error(f"Stdout: {e.stdout}")
        LILYPAD_JOBS[job_id]["status"] = "error"
        LILYPAD_JOBS[job_id]["result"] = {
            "status": "error",
            "message": e.stderr or e.stdout
        }
    except Exception as e:
        # Handle general errors
        logger.error(f"Error in Lilypad evaluation for job {job_id}: {str(e)}")
        LILYPAD_JOBS[job_id]["status"] = "error"
        LILYPAD_JOBS[job_id]["result"] = {
            "status": "error",
            "message": str(e)
        }


@router.post("/evaluate_lilypad_focus")
async def evaluate_lilypad_focus(
    file: UploadFile = File(...),
    user_address: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Evaluate an uploaded image's focus measure with your Lilypad module.
    Returns a job ID for status polling.
    """
    import base64

    try:
        # 1. Create a unique job ID
        job_id = str(uuid.uuid4())
        LILYPAD_JOBS[job_id] = {"status": "pending", "result": None}
        
        logger.info(f"Starting Lilypad focus-eval job {job_id} for user {user_address}")
        
        # 2. Read the uploaded file bytes
        file_bytes = await file.read()
        if not file_bytes:
            raise ValueError("Empty file or failed to read bytes")

        # 3. Base64-encode the file
        file_b64 = base64.b64encode(file_bytes).decode("utf-8")
        
        # 4. Kick off background task
        background_tasks.add_task(
            run_lilypad_focus_evaluation,
            file_b64,
            job_id
        )

        return {
            "success": True,
            "job_id": job_id,
            "status": "processing",
            "message": "Lilypad focus evaluation started"
        }

    except Exception as e:
        logger.error(f"Lilypad focus evaluation error: {str(e)}")
        # If job_id was created, mark it failed
        if "job_id" in locals():
            LILYPAD_JOBS[job_id]["status"] = "failed"
            LILYPAD_JOBS[job_id]["result"] = {
                "status": "error",
                "message": str(e)
            }
            return {
                "success": False,
                "error": str(e),
                "job_id": job_id,
                "status": "failed"
            }
        
        # Fallback if no job_id
        return {
            "success": False,
            "error": str(e),
            "status": "failed"
        }

async def run_lilypad_focus_evaluation(file_b64: str, job_id: str):
    """
    Background task to run the "focus measure" Lilypad module.
    Expects 'INPUT' to be base64 of the image bytes.
    """
    import subprocess
    import os

    try:
        env_vars = os.environ.copy()
        env_vars["WEB3_PRIVATE_KEY"] = settings.WEB3_PRIVATE_KEY
        
        # We'll pass the file bytes as a base64 string in -i
        command = [
            "lilypad",
            "run",
            "github.com/ce20480/lilypad-module-focus-measure:74541ee759a92d8dd19d7fdf8a835eae57168e76",
            "-i",
            f'INPUT={file_b64}'  # no extra quotes, to avoid double quoting
        ]
        
        logger.info(f"Running Lilypad focus command for job {job_id}")
        logger.info(f"Command: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True,
            env=env_vars
        )
        
        # Log output (for debugging)
        logger.info(f"Lilypad job stdout (truncated): {result.stdout[:500]}...")
        if result.stderr:
            logger.warning(f"Lilypad job stderr: {result.stderr}")
        
        # *** 5. Parse the local path from stdout ***
        lines = result.stdout.strip().split("\n")
        path_line = None
        
        for line in reversed(lines):
            if "open /tmp/lilypad/data/downloaded-files" in line:
                path_line = line.strip()
                break
        
        # fallback to regex
        if not path_line:
            pattern = r"open\s+(/tmp/lilypad/data/downloaded-files/\S+)"
            match = re.search(pattern, result.stdout)
            if match:
                dir_path = match.group(1)
                file_path = os.path.join(dir_path, "outputs", "result.json")
            else:
                logger.error("Could not find output path in Lilypad response.")
                LILYPAD_JOBS[job_id]["status"] = "error"
                LILYPAD_JOBS[job_id]["result"] = {
                    "status": "error",
                    "message": "No output path found in Lilypad logs."
                }
                return
        else:
            path_line = path_line.replace("open ", "")
            file_path = os.path.join(path_line, "outputs", "result.json")
        
        # *** 6. Load /outputs/result.json ***
        if not os.path.exists(file_path):
            logger.error(f"No result.json at {file_path}")
            LILYPAD_JOBS[job_id]["status"] = "error"
            LILYPAD_JOBS[job_id]["result"] = {
                "status": "error",
                "message": f"Could not find result.json at {file_path}"
            }
            return
        
        with open(file_path, "r") as fp:
            file_data = json.load(fp)
        
        # The module writes: {"output": {"success": <bool>, "focus_measure": <float>, "score": <float>, "threshold": <float>}}
        # or possibly an error. Let's assume "output" is success if "status" != "error".
        output = file_data.get("output", {})
        if output.get("status") == "error":
            logger.error(f"Focus measure module returned error: {output.get('message')}")
            LILYPAD_JOBS[job_id]["status"] = "error"
            LILYPAD_JOBS[job_id]["result"] = output
        else:
            # success
            LILYPAD_JOBS[job_id]["status"] = "completed"
            LILYPAD_JOBS[job_id]["result"] = output

    except subprocess.CalledProcessError as e:
        logger.error(f"Focus measure Lilypad subprocess error for job {job_id}: {e}")
        LILYPAD_JOBS[job_id]["status"] = "error"
        LILYPAD_JOBS[job_id]["result"] = {
            "status": "error",
            "message": e.stderr or e.stdout
        }
    except Exception as e:
        logger.error(f"General error in focus measure module for job {job_id}: {str(e)}")
        LILYPAD_JOBS[job_id]["status"] = "error"
        LILYPAD_JOBS[job_id]["result"] = {
            "status": "error",
            "message": str(e)
        }


@router.get("/lilypad/status/{job_id}")
async def get_lilypad_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get the status of a Lilypad evaluation job
    """
    if job_id not in LILYPAD_JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_data = LILYPAD_JOBS[job_id]
    
    # Format response to ensure it has consistent structure
    response = {
        "status": job_data["status"],
    }
    
    # Include result if available
    if job_data["result"]:
        response["result"] = job_data["result"]
        
        # If status is error, ensure we're propagating the error correctly
        if job_data["status"] == "error":
            # Check if there's a nested error in the output field
            if isinstance(job_data["result"], dict) and "output" in job_data["result"] and job_data["result"]["output"].get("status") == "error":
                # Add error message to the top level for easier access
                response["error"] = job_data["result"]["output"].get("message", "Unknown error")
    
    return response