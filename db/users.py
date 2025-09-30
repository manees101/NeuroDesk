from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
class User(BaseModel):
    id: str
    name: str
    email: EmailStr
    hashed_password: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserPublic(BaseModel):
    id: str
    name: str
    email: EmailStr
    created_at: datetime

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class PasswordResetToken(BaseModel):
    user_id: str
    email: EmailStr
    token: str
    expires_at: datetime
    used: bool = False
    created_at: datetime = Field(default_factory=datetime.now)

class EmailLog(BaseModel):
    email: EmailStr
    subject: str
    content: str
    type: str  # e.g., "password_reset"
    status: str = "pending"  # pending | sent | cancelled | failed
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class UserChat(BaseModel):
    user_id: str
    query: str
    retrieved_documents: Optional[str]
    llm_response: str
    collection_name: Optional[str] = None
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