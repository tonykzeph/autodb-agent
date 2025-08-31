from pydantic import BaseModel, Field, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema
from typing import Optional, Any
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: Any
    ) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate),
                ])
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return handler(core_schema.str_schema())

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

class DocumentUploadResponse(BaseModel):
    id: str = Field(alias="_id")
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    storage_key: str
    storage_url: str
    uploaded_at: datetime
    
    # AI Processing metadata
    ai_workflow: Optional[dict] = None
    processing_results: Optional[dict] = None
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }

class DocumentModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    storage_key: str
    storage_url: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    
    # AI Processing metadata
    ai_workflow: Optional[dict] = None
    processing_results: Optional[dict] = None
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }