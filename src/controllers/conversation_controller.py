"""
Sohbet (conversation) listeleme ve geçmiş mesajları getirme iş mantığı.
"""

import logging
import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.db_schemes.hocaya_sor.schemes.conversation import Conversation
from models.db_schemes.hocaya_sor.schemes.question_log import QuestionLog
from models.db_schemes.hocaya_sor.schemes.question_feedback import QuestionFeedback
from models.db_schemes.hocaya_sor.schemes.fatwa import Fatwa
from models.schemas.conversation_schemas import ConversationResponse, ConversationMessageResponse
from models.schemas.fatwa_schemas import FatwaSource
from models.enums.ResponseEnums import ResponseSignal

logger = logging.getLogger(__name__)


async def list_conversations(user_id: uuid.UUID, db: Session) -> list[ConversationResponse]:
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [ConversationResponse.model_validate(c) for c in conversations]


async def get_conversation_messages(
    conversation_id: uuid.UUID, user_id: uuid.UUID, db: Session
) -> list[ConversationMessageResponse]:
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation is None:
        raise HTTPException(status_code=404, detail=ResponseSignal.CONVERSATION_NOT_FOUND.value)
    if conversation.user_id != user_id:
        raise HTTPException(status_code=403, detail=ResponseSignal.CONVERSATION_FORBIDDEN.value)

    logs = (
        db.query(QuestionLog)
        .filter(QuestionLog.conversation_id == conversation_id)
        .order_by(QuestionLog.created_at.asc())
        .all()
    )

    messages: list[ConversationMessageResponse] = []
    for log in logs:
        fatwas = (
            db.query(Fatwa).filter(Fatwa.id.in_(log.retrieved_fatwa_ids)).all()
            if log.retrieved_fatwa_ids
            else []
        )
        fatwa_by_id = {str(f.id): f for f in fatwas}
        sources = [
            FatwaSource(
                id=str(fid),
                question=fatwa_by_id[str(fid)].question,
                answer=fatwa_by_id[str(fid)].answer,
                main_category=fatwa_by_id[str(fid)].main_category,
                source_dataset=fatwa_by_id[str(fid)].source_dataset,
                source_url=fatwa_by_id[str(fid)].source_url,
            )
            for fid in log.retrieved_fatwa_ids
            if str(fid) in fatwa_by_id
        ]

        feedback = (
            db.query(QuestionFeedback)
            .filter(QuestionFeedback.question_log_id == log.id)
            .first()
        )

        messages.append(
            ConversationMessageResponse(
                log_id=log.id,
                question=log.question,
                answer=log.answer,
                sources=sources,
                feedback=feedback.feedback if feedback else None,
                comment=feedback.comment if feedback else None,
                created_at=log.created_at,
            )
        )

    return messages