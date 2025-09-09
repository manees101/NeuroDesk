from pydantic import BaseModel
from typing import Optional

class FeedbackRequest(BaseModel):
    user_id: Optional[str] = None  # Deprecated: user is derived from auth token
    is_positive_feedback: bool
    query: Optional[str] = None
    comments: Optional[str] = None
