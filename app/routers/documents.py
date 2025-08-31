from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from datetime import datetime
import uuid
import os
from typing import List

from app.models import DocumentModel, DocumentUploadResponse
from app.database import get_database
from app.services.storage import R2StorageService
from app.interfaces import StorageInterface

router = APIRouter(prefix="/documents", tags=["documents"])

def get_storage_service() -> StorageInterface:
    return R2StorageService()

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    storage_service: StorageInterface = Depends(get_storage_service)
):
    """Upload a document to R2 storage and save metadata to MongoDB"""
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    storage_key = f"documents/{unique_filename}"
    
    try:
        # Upload to R2 storage
        storage_url = await storage_service.upload_file(
            file=file.file,
            key=storage_key,
            content_type=file.content_type
        )
        
        # Create document model
        document = DocumentModel(
            filename=unique_filename,
            original_filename=file.filename,
            file_size=file.size or 0,
            content_type=file.content_type or "application/octet-stream",
            storage_key=storage_key,
            storage_url=storage_url
        )
        
        # Save to MongoDB
        db = get_database()
        result = await db.documents.insert_one(document.model_dump(by_alias=True))
        document.id = result.inserted_id
        
        return DocumentUploadResponse(**document.model_dump(by_alias=True))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/", response_model=List[DocumentUploadResponse])
async def list_documents():
    """Get all uploaded documents"""
    db = get_database()
    documents = await db.documents.find().to_list(100)
    return [DocumentUploadResponse(**doc) for doc in documents]

@router.get("/{document_id}", response_model=DocumentUploadResponse)
async def get_document(document_id: str):
    """Get a specific document by ID"""
    db = get_database()
    
    try:
        from bson import ObjectId
        document = await db.documents.find_one({"_id": ObjectId(document_id)})
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return DocumentUploadResponse(**document)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid document ID")