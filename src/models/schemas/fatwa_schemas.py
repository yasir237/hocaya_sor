"""
API request/response Pydantic şemaları.
"""

import uuid
from pydantic import BaseModel, Field

from models.enums.FeedbackEnum import FeedbackTypeEnum as FeedbackType


class AskRequest(BaseModel):
    conversation_id: uuid.UUID | None = Field(
        default=None, description="Var olan bir sohbete devam etmek için ID. Boş bırakılırsa yeni sohbet oluşturulur."
    )
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
    conversation_id: uuid.UUID
    log_id: uuid.UUID
    question: str
    answer: str
    sources: list[FatwaSource]


class FeedbackRequest(BaseModel):
    feedback: FeedbackType
    comment: str | None = Field(default=None, max_length=1000, description="Opsiyonel yorum")


class FeedbackResponse(BaseModel):
    question_log_id: uuid.UUID
    feedback: FeedbackType
    comment: str | None = None