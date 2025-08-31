from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import os
from typing import Optional

# Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "autodb_agent")

class AsyncDatabase:
    client: Optional[AsyncIOMotorClient] = None
    database = None

async_db = AsyncDatabase()

async def connect_to_mongo():
    """Create database connection"""
    async_db.client = AsyncIOMotorClient(MONGODB_URL)
    async_db.database = async_db.client[DATABASE_NAME]

async def close_mongo_connection():
    """Close database connection"""
    if async_db.client:
        async_db.client.close()

def get_database():
    """Get database instance for async operations"""
    return async_db.database

# Sync client for migrations or admin tasks
def get_sync_client():
    """Get synchronous MongoDB client"""
    return MongoClient(MONGODB_URL)