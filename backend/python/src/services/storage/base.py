from abc import ABC, abstractmethod
from typing import BinaryIO, Union, Dict, Any, Optional, List

class StorageProvider(ABC):
    """Base class for storage providers"""
    
    @abstractmethod
    async def upload_file(
        self, 
        bucket_name: str,
        file_data: Union[bytes, BinaryIO],
        file_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload a file and return file information
        
        Returns:
            Dict with at least 'id' or 'cid' key identifying the file
        """
        pass

    @abstractmethod
    async def list_files(self, bucket_name: str, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all files in a bucket
        
        Returns:
            List of file metadata dictionaries
        """
        pass

    @abstractmethod 
    async def download_file(
        self, 
        bucket_name: str, 
        file_name: str, 
        destination: Optional[str] = None
    ) -> Union[str, bytes]:
        """
        Download a file from storage
        
        Args:
            destination: If provided, save to this path and return path
                         If None, return file contents as bytes
        
        Returns:
            Path to downloaded file as string, or bytes contents
        """
        pass
        
    @abstractmethod
    async def delete_file(self, bucket_name: str, file_name: str) -> bool:
        """Delete a file and return success status"""
        pass
        
    @abstractmethod
    async def get_file_metadata(self, bucket_name: str, file_name: str) -> Dict[str, Any]:
        """Get metadata for a specific file"""
        pass 