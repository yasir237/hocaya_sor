"""
API request/response Pydantic şemaları.
"""

import uuid
from pydantic import BaseModel, Field

from models.enums.FeedbackEnum import FeedbackTypeEnum as FeedbackType


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000, description="Kullanıcının sorusu")
    top_k: int = Field(default=5, ge=1, le=10, description="Kaç fetva getirilsin (1-10)")


class FatwaSource(BaseModel):
    id: str
    question: str
    answer: str
    main_category: str
    source_dataset: str
    source_url: str | None = None


class AskResponse(BaseModel):
    log_id: uuid.UUID
    question: str
    answer: str
    sources: list[FatwaSource]


class FeedbackRequest(BaseModel):
    feedback: FeedbackType


class FeedbackResponse(BaseModel):
    question_log_id: uuid.UUID
    feedback: FeedbackType