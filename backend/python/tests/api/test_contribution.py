import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import UploadFile
from io import BytesIO

from src.api.routes.storage import upload_file
from src.services.evaluator import EvaluatorService, EvaluationStatus, EvaluationResult
from src.services.contribution_service import ContributionService

# Test data
TEST_USER_ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"
TEST_IMAGE_CONTENT = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdb\xfa\x0e\xea\x00\x00\x00\x00IEND\xaeB`\x82"  # Small valid PNG image
TEST_TASK_ID = "test-task-id"
TEST_FILE_ID = "test-file-id"

# Create async context manager for background tasks
class MockBackgroundTasks:
    def __init__(self):
        self.tasks = []
        
    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))


@pytest.mark.asyncio
async def test_contribution_endpoint():
    """Test the contribution endpoint workflow"""
    
    # Mock contribution service
    mock_contribution_service = AsyncMock(spec=ContributionService)
    mock_contribution_service.submit_contribution.return_value = {
        "task_id": TEST_TASK_ID,
        "file_id": TEST_FILE_ID,
        "filename": "test.png",
        "file_size": len(TEST_IMAGE_CONTENT),
        "content_type": "image/png",
        "user_address": TEST_USER_ADDRESS,
        "submission_time": 1234567890.0,
    }
    
    # Create a mock file
    file_content = BytesIO(TEST_IMAGE_CONTENT)
    file = UploadFile(filename="test.png", file=file_content, content_type="image/png")
    
    # Create mock background tasks
    background_tasks = MockBackgroundTasks()
    
    # Call the endpoint with mocked services
    with patch("src.api.routes.storage.get_contribution_service", return_value=mock_contribution_service):
        response = await upload_file(
            file=file,
            user_address=TEST_USER_ADDRESS,
            background_tasks=background_tasks
        )
    
    # Check the response
    assert response["success"] is True
    assert response["task_id"] == TEST_TASK_ID
    assert response["status_endpoint"] == f"/storage/evaluation/{TEST_TASK_ID}"
    
    # Check that submit_contribution was called with correct parameters
    mock_contribution_service.submit_contribution.assert_called_once()
    call_args = mock_contribution_service.submit_contribution.call_args[1]
    assert call_args["file_name"] == "test.png"
    assert call_args["file_type"] == "image/png"
    assert call_args["user_address"] == TEST_USER_ADDRESS
    
    # Check that background task was scheduled
    assert len(background_tasks.tasks) == 1
    task_func, task_args, _ = background_tasks.tasks[0]
    assert task_func == mock_contribution_service.process_evaluation_workflow
    assert task_args[0] == TEST_TASK_ID  # task_id
    assert task_args[1] == TEST_USER_ADDRESS  # user_address


@pytest.mark.asyncio
async def test_contribution_status_endpoint():
    """Test the contribution status endpoint"""
    
    # Mock contribution service
    mock_contribution_service = AsyncMock(spec=ContributionService)
    mock_contribution_service.get_contribution_status.return_value = {
        "task_id": TEST_TASK_ID,
        "status": EvaluationStatus.APPROVED,
        "message": "Contribution approved",
        "completed": True,
        "score": 0.9,
        "phases": {
            "evaluation": {
                "status": "completed",
                "success": True,
                "time": 1234567890.0,
                "details": {
                    "blur_score": 0.85,
                    "landmark_score": 0.95
                }
            },
            "upload": {
                "status": "completed",
                "success": True,
                "time": 1234567891.0,
                "details": {
                    "cid": "test-cid",
                    "bucket": "test-bucket"
                }
            },
            "reward": {
                "status": "completed",
                "success": True,
                "time": 1234567892.0,
                "details": {
                    "xp": {
                        "success": True,
                        "amount": 100,
                        "transaction_hash": "0xabcdef"
                    }
                }
            }
        }
    }
    
    # Call the endpoint with mocked services
    from src.api.routes.storage import get_evaluation_status
    with patch("src.api.routes.storage.get_contribution_service", return_value=mock_contribution_service):
        response = await get_evaluation_status(task_id=TEST_TASK_ID)
    
    # Check the response
    assert response["task_id"] == TEST_TASK_ID
    assert response["status"] == EvaluationStatus.APPROVED
    assert response["completed"] is True
    assert response["score"] == 0.9
    assert "phases" in response
    assert response["phases"]["evaluation"]["success"] is True
    assert response["phases"]["upload"]["success"] is True
    assert response["phases"]["reward"]["success"] is True
    
    # Check that get_contribution_status was called with correct parameters
    mock_contribution_service.get_contribution_status.assert_called_once_with(TEST_TASK_ID) 