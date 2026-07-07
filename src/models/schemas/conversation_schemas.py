"""
Sohbet (conversation) listeleme ve mesaj geçmişi için Pydantic şemaları.
"""

import datetime
import uuid
from pydantic import BaseModel

from typing import Optional
from models.schemas.fatwa_schemas import FatwaSource
from models.enums.FeedbackEnum import FeedbackTypeEnum as FeedbackType


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class ConversationMessageResponse(BaseModel):
    log_id: uuid.UUID
    question: str
    answer: str
    sources: list[FatwaSource]
    feedback: FeedbackType | None = None
    comment: str | None = None
    created_at: datetime.datetime

 
 
class ConversationMessagesPage(BaseModel):
    items: list[ConversationMessageResponse]
    has_more: bool
    # "{created_at_iso}|{log_id}" formatında birleşik cursor.
    # Bir sonraki istekte `before` parametresine aynen geçilir.
    next_cursor: Optional[str] = None