from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form
from typing import Dict, Any
from ...services.storage.akave_sdk import AkaveSDK, AkaveConfig, AkaveError
from ...services.evaluator import ContributionEvaluator
from ...core.config import settings
# from ...services.reward_service import RewardService
import os
import uuid

router = APIRouter(prefix="/storage", tags=["storage"])
evaluator = ContributionEvaluator()
# reward_service = RewardService()

@router.post("/contribution/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_address: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> Dict[str, Any]:
    """
    Handle file upload with evaluation and rewards
    """
    if not user_address:
        raise HTTPException(400, "User address is required for rewards")
        
    try:
        # 1. Upload to storage
        async with AkaveSDK(AkaveConfig()) as akave:
            upload_result = await akave.upload_file(
                "contributions",  # bucket name
                await file.read(),
                file.filename
            )
        
        # 2. Create a unique task ID
        task_id = str(uuid.uuid4())
        
        # 3. Submit for evaluation
        await evaluator.submit_for_evaluation(
            task_id=task_id,
            file_id=upload_result["fileId"],
            file_type=file.content_type,
            user_address=user_address,
            metadata={
                "filename": file.filename,
                "content_type": file.content_type,
                "size": file.size,
                "ipfs_hash": upload_result.get("ipfsHash", "")
            }
        )
        
        # 4. Process evaluation in background
        background_tasks.add_task(
            evaluator.process_evaluation_and_reward,
            task_id,
            user_address,
            upload_result
        )
        
        return {
            "success": True,
            "message": "File uploaded and submitted for evaluation",
            "task_id": task_id,
            "upload_result": upload_result
        }
        
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {str(e)}")

async def process_evaluation_and_reward(
    task_id: str,
    user_address: str,
    upload_result: Dict[str, Any]
) -> None:
    """
    Background task to process evaluation and award tokens
    """
    try:
        # Wait for evaluation result
        evaluation_result = await evaluator._process_evaluation({
            "task_id": task_id,
            "file_id": upload_result["fileId"],
            "metadata": upload_result
        })
        
        # Process rewards if evaluation passed
        reward_result = await reward_service.process_evaluation_result(
            user_address,
            evaluation_result,
            {
                "ipfs_hash": upload_result.get("ipfsHash", ""),
                "file_id": upload_result["fileId"],
                "task_id": task_id
            }
        )
        
        # TODO: Store results in database
        print(f"Evaluation and reward processing completed: {reward_result}")
        
    except Exception as e:
        print(f"Error processing evaluation and reward: {e}")

@router.get("/evaluation/{task_id}")
async def get_evaluation_status(task_id: str) -> Dict[str, Any]:
    """
    Get the status of an evaluation task
    """
    result = await evaluator.get_evaluation_status(task_id)
    if not result:
        raise HTTPException(404, "Evaluation task not found")
    return {
        "task_id": task_id,
        "status": result.status.value,
        "score": result.score,
        "feedback": result.feedback,
        "timestamp": result.timestamp.isoformat(),
        "metadata": result.metadata
    } 

@router.get('/files')
async def list_files() -> Dict[str, Any]:
    """List all files"""
    try:
        files = await self.storage_service.list_files(settings.DEFAULT_BUCKET)
        return {"files": files}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list files: {str(e)}"
        )

@router.post('/upload')
async def upload_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload a file to Akave storage.
    Supports binary files (images, videos, etc.)
    """
    try:
        # Read file as bytes
        contents = await file.read()
        file_size = len(contents)

        # Size validations
        if file_size < 127:
            raise HTTPException(
                status_code=400,
                detail="File size must be at least 127 bytes"
            )
        if file_size > 100 * 1024 * 1024:  # 100MB
            raise HTTPException(
                status_code=400,
                detail="File size must not exceed 100MB"
            )

        print(f"Processing file: {file.filename}, size: {file_size} bytes")
        
        # Initialize Akave SDK with proper configuration
        akave_config = AkaveConfig(host="http://localhost:4000")  # Docker container port
        akave_sdk = AkaveSDK(akave_config)

        async with akave_sdk as client:  # Use initialized SDK
            result = await client.upload_file(
                bucket_name="asl-training-data",
                file_data=contents,
                file_name=file.filename
            )

            return {
                "message": "File uploaded successfully",
                "filename": file.filename,
                "size": file_size,
                "cid": result.get("cid", ""),
                "bucket": "asl-training-data",
                "contentType": file.content_type
            }

    except AkaveError as e:
        print(f"Akave error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Storage error: {str(e)}"
        )
    except Exception as e:
        print(f"Upload error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )