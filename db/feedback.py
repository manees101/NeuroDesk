from pydantic import BaseModel
from typing import Optional

class FeedbackRequest(BaseModel):
    user_id: str
    is_positive_feedback: bool
    query: Optional[str] = None
    comments: Optional[str] = None
