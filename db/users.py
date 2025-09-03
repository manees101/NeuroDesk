from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class User(BaseModel):
    id: str
    name: str
    email: str
    password: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class UserChat(BaseModel):
    user_id: str
    query: str
    retrieved_documents: Optional[str]
    llm_response: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

class DocSummary(BaseModel):
    user_id: str = Field(..., description="The ID of the user who uploaded the PDF")
    filename: str = Field(..., description="Original PDF filename")
    collection_name: str = Field(..., description="ChromaDB collection linked to this file")
    summary: str = Field(..., description="LLM generated summary of the PDF")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of creation")
    updated_at: Optional[datetime] = Field(default=None, description="Timestamp of last update")