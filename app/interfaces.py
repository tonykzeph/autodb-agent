from abc import ABC, abstractmethod
from typing import Optional, BinaryIO

class StorageInterface(ABC):
    @abstractmethod
    async def upload_file(
        self,
        file: BinaryIO,
        key: str,
        content_type: Optional[str] = None
    ) -> str:
        """Upload a file and return the URL"""
        pass

    @abstractmethod
    async def delete_file(self, key: str) -> bool:
        """Delete a file and return success status"""
        pass

    @abstractmethod
    async def get_file_url(self, key: str) -> str:
        """Get the public URL of a file"""
        pass