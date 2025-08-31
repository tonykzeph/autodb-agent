import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import os
from typing import Optional, BinaryIO
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.interfaces import StorageInterface

class R2StorageService(StorageInterface):
    def __init__(self):
        self.access_key_id = os.getenv("R2_ACCESS_KEY_ID")
        self.secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY")
        self.endpoint_url = os.getenv("R2_ENDPOINT_URL")
        self.bucket_name = os.getenv("R2_BUCKET_NAME")
        self.region = os.getenv("R2_REGION", "auto")
        
        if not all([self.access_key_id, self.secret_access_key, self.endpoint_url, self.bucket_name]):
            raise ValueError("Missing required R2 storage environment variables")
        
        self.client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region,
            config=Config(signature_version='s3v4')
        )
        
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def upload_file(
        self,
        file: BinaryIO,
        key: str,
        content_type: Optional[str] = None
    ) -> str:
        """Upload a file to R2 storage"""
        loop = asyncio.get_event_loop()
        
        try:
            await loop.run_in_executor(
                self.executor,
                self._upload_file_sync,
                file,
                key,
                content_type
            )
            return await self.get_file_url(key)
        except ClientError as e:
            raise Exception(f"Failed to upload file: {str(e)}")

    def _upload_file_sync(self, file: BinaryIO, key: str, content_type: Optional[str]):
        """Synchronous upload helper"""
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
            
        self.client.upload_fileobj(
            file,
            self.bucket_name,
            key,
            ExtraArgs=extra_args
        )

    async def delete_file(self, key: str) -> bool:
        """Delete a file from R2 storage"""
        loop = asyncio.get_event_loop()
        
        try:
            await loop.run_in_executor(
                self.executor,
                lambda: self.client.delete_object(Bucket=self.bucket_name, Key=key)
            )
            return True
        except ClientError:
            return False

    async def get_file_url(self, key: str) -> str:
        """Get the public URL of a file"""
        return f"{self.endpoint_url}/{self.bucket_name}/{key}"