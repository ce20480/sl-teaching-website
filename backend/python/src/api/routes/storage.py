from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form
from typing import Dict, Any
from ...services.storage.akave_sdk import AkaveError
from ...services.service_container import get_contribution_service, get_storage_sdk, initialize_services
import logging

# Initialize all services
initialize_services()

router = APIRouter(prefix="/storage", tags=["storage"])
logger = logging.getLogger(__name__)

@router.post("/contribution")
async def upload_file(
    file: UploadFile = File(...),
    user_address: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> Dict[str, Any]:
    """
    Handle file upload with a three-phase process:
    1. Evaluate image quality
    2. Upload approved images
    3. Reward users for approved contributions
    """
    if not user_address:
        raise HTTPException(400, "User address is required for rewards")
    
    logger.info(f"Processing contribution from address: {user_address}")
    
    # Get contribution service from container    
    contribution_service = get_contribution_service()
    
    try:
        # 1. Read file contents
        contents = await file.read()
        
        # Check file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(400, "Only image files are accepted")
        
        # 2. Submit contribution to service
        task_metadata = await contribution_service.submit_contribution(
            file_content=contents,
            file_name=file.filename,
            file_type=file.content_type,
            user_address=user_address
        )
        
        # Get task ID from metadata
        task_id = task_metadata["task_id"]
        
        # 3. Start evaluation workflow in background
        background_tasks.add_task(
            contribution_service.process_evaluation_workflow,
            task_id,
            user_address,
            contents,
            task_metadata
        )
        
        # 4. Return immediate response with task ID for status tracking
        return {
            "success": True,
            "message": "Contribution submitted for evaluation",
            "task_id": task_id,
            "status_endpoint": f"/api/evaluation/status/{task_id}"
        }
        
    except Exception as e:
        logger.error(f"Contribution upload error: {str(e)}")
        raise HTTPException(500, f"Upload failed: {str(e)}")

@router.get("/evaluation/status/{task_id}")
async def get_evaluation_status(task_id: str) -> Dict[str, Any]:
    """
    Get the status of an evaluation task with detailed phase information
    """
    try:
        # Get status from contribution service
        contribution_service = get_contribution_service()
        return await contribution_service.get_contribution_status(task_id)
        
    except Exception as e:
        logger.error(f"Error getting evaluation status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get evaluation status: {str(e)}"
        )

@router.get('/files')
async def list_files() -> Dict[str, Any]:
    """List all files"""
    try:
        akave_sdk = get_storage_sdk()
        async with akave_sdk as client:
            files = await client.list_files("asl-training-data")
            return {"files": files}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list files: {str(e)}"
        )

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

        logger.info(f"Processing file: {file.filename}, size: {file_size} bytes")
        
        akave_sdk = get_storage_sdk()
        async with akave_sdk as client:
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
        logger.error(f"Akave error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Storage error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )