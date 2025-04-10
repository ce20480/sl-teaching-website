from typing import Dict, Any, Optional, BinaryIO, Union
from pathlib import Path
import aiohttp
from dataclasses import dataclass
import os

@dataclass
class AkaveConfig:
    """Configuration for Akave SDK"""
    host: str = "http://localhost:4000"  # Default to our Docker container port
    timeout: int = 30

class AkaveError(Exception):
    """Custom exception for Akave SDK errors"""
    pass

class AkaveSDK:
    """Python SDK for Akave API"""
    
    def __init__(self, config: Optional[AkaveConfig] = None):
        self.config = config or AkaveConfig()
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            base_url=self.config.host,
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, BinaryIO]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Akave API"""
        if not self._session:
            raise RuntimeError("SDK must be used as async context manager")
            
        try:
            # Prepare request data
            kwargs = {}
            if data:
                kwargs['json'] = data
            if files:
                form = aiohttp.FormData()
                for key, file in files.items():
                    form.add_field(key, file)
                kwargs['data'] = form
            
            async with self._session.request(method, endpoint, **kwargs) as response:
                response_data = await response.json()
                if not response.ok:
                    raise AkaveError(
                        f"API request failed: {response_data.get('error', 'Unknown error')}"
                    )
                return response_data
                
        except aiohttp.ClientError as e:
            raise AkaveError(f"Network error: {str(e)}")
    
    # Bucket Operations
    async def create_bucket(self, bucket_name: str) -> Dict[str, Any]:
        """Create a new storage bucket"""
        return await self._request('POST', '/buckets', {'bucketName': bucket_name})
    
    async def list_buckets(self) -> Dict[str, Any]:
        """List all buckets"""
        return await self._request('GET', '/buckets')
    
    async def get_bucket(self, bucket_name: str) -> Dict[str, Any]:
        """Get bucket details"""
        return await self._request('GET', f'/buckets/{bucket_name}')
    
    # File Operations
    async def list_files(self, bucket_name: str) -> Dict[str, Any]:
        """List files in a bucket"""
        return await self._request('GET', f'/buckets/{bucket_name}/files')
    
    async def get_file_info(self, bucket_name: str, file_name: str) -> Dict[str, Any]:
        """Get file metadata"""
        return await self._request('GET', f'/buckets/{bucket_name}/files/{file_name}')
    
    async def upload_file(
        self, 
        bucket_name: str, 
        file_data: Union[bytes, BinaryIO, Path], 
        file_name: str
    ) -> Dict[str, Any]:
        """Upload a file to a bucket using FormData"""
        if not self._session:
            raise RuntimeError("SDK must be used as async context manager")

        # Create FormData
        form = aiohttp.FormData()
        
        try:
            if isinstance(file_data, bytes):
                form.add_field('file', 
                    file_data,
                    filename=file_name,
                    content_type='application/octet-stream'
                )
            elif isinstance(file_data, Path):
                form.add_field('file',
                    file_data.open('rb'),
                    filename=file_name,
                    content_type='application/octet-stream'
                )
            else:  # BinaryIO
                form.add_field('file',
                    file_data,
                    filename=file_name,
                    content_type='application/octet-stream'
                )

            async with self._session.post(
                f'/buckets/{bucket_name}/files',
                data=form
            ) as response:
                if not response.ok:
                    text = await response.text()
                    raise AkaveError(f"Upload failed: {text}")
                return await response.json()

        except Exception as e:
            raise AkaveError(f"Upload error: {str(e)}")
    
    async def download_file(
        self, 
        bucket_name: str, 
        file_name: str, 
        output_path: Optional[Union[str, Path]] = None
    ) -> Union[bytes, Path]:
        """Download a file from a bucket"""
        async with self._session.get(
            f'/buckets/{bucket_name}/files/{file_name}/download'
        ) as response:
            if not response.ok:
                raise AkaveError(f"Download failed: {response.status}")
                
            content = await response.read()
            
            if output_path:
                path = Path(output_path)
                path.write_bytes(content)
                return path
            return content

    def _load_private_key(self, key_path: str) -> str:
        path = os.path.expanduser(key_path)
        with open(path, 'r') as f:
            return f.read().strip()
    
    def _ensure_bucket_exists_cli(self):
        try:
            self._run_command(
                f'akavecli ipc bucket create {self.default_bucket} '
                f'--node-address={self.node_address} '
                f'--private-key "{self.private_key}"'
            )
        except Exception as e:
            if "already exists" not in str(e):
                raise e
    
    async def create_bucket_cli(self, bucket_name: str) -> str:
        command = (
            f'akavecli ipc bucket create {bucket_name} '
            f'--node-address={self.node_address} '
            f'--private-key "{self.private_key}"'
        )
        stdout, _ = self._run_command(command)
        return stdout

    async def upload_file_cli(
        self, 
        bucket_name: str, 
        file_data: Union[bytes, BinaryIO], 
        file_name: str
    ) -> str:
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(delete=False) as temp_file:
            # Handle both bytes and BinaryIO
            if isinstance(file_data, bytes):
                temp_file.write(file_data)
            else:
                temp_file.write(file_data.read())
            
            temp_file.flush()
            
            try:
                command = (
                    f'akavecli ipc file upload {bucket_name} {temp_file.name} '
                    f'--name {file_name} '
                    f'--node-address={self.node_address} '
                    f'--private-key "{self.private_key}"'
                )
                stdout, _ = self._run_command(command)
                return stdout.strip()  # Remove any whitespace
            finally:
                os.unlink(temp_file.name)  # Clean up temp file

    async def download_file_cli(self, bucket_name: str, file_name: str, destination: str) -> str:
        command = (
            f'akavecli ipc file download {bucket_name} {file_name} {destination} '
            f'--node-address={self.node_address} '
            f'--private-key "{self.private_key}"'
        )
        stdout, _ = self._run_command(command)
        return stdout

    async def list_files_cli(self, bucket_name: str) -> str:
        command = (
            f'akavecli ipc file list {bucket_name} '
            f'--node-address={self.node_address} '
            f'--private-key "{self.private_key}"'
        )
        stdout, _ = self._run_command(command)
        return stdout
    
    def _run_command(self, command: str) -> tuple[str, str]:
        import subprocess
        print(f"Executing command: {command}")
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            error_msg = f"Command failed with code {process.returncode}: {stderr}"
            print(error_msg)
            raise Exception(error_msg)
            
        print(f"Command output: {stdout}")
        return stdout, stderr
