"""
Sohbet (conversation) listeleme ve geçmiş mesajları getirme iş mantığı.
"""

import logging
import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session

from typing import Optional
from datetime import datetime
from sqlalchemy import tuple_

from models.db_schemes.hocaya_sor.schemes.conversation import Conversation
from models.db_schemes.hocaya_sor.schemes.question_log import QuestionLog
from models.db_schemes.hocaya_sor.schemes.question_feedback import QuestionFeedback
from models.db_schemes.hocaya_sor.schemes.fatwa import Fatwa
from models.schemas.conversation_schemas import ConversationResponse, ConversationMessageResponse, ConversationMessagesPage
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


def _build_message_responses(logs: list[QuestionLog], db: Session) -> list[ConversationMessageResponse]:
    """
    Bir grup QuestionLog satırını ConversationMessageResponse'a çevirir.
    Kaynaklar (retrieved_fatwa_ids) ve feedback ayrı tablolarda tutulduğu için,
    her satır için tek tek sorgu atmak yerine tüm grup için toplu çekilir.
    """
    if not logs:
        return []

    # ---- Tüm gruptaki fetva id'lerini tek seferde çek ----
    all_fatwa_ids: set[str] = set()
    for log in logs:
        if log.retrieved_fatwa_ids:
            all_fatwa_ids.update(str(fid) for fid in log.retrieved_fatwa_ids)

    fatwa_by_id: dict[str, Fatwa] = {}
    if all_fatwa_ids:
        fatwas = db.query(Fatwa).filter(Fatwa.id.in_(all_fatwa_ids)).all()
        fatwa_by_id = {str(f.id): f for f in fatwas}

    # ---- Tüm gruptaki feedback'leri tek seferde çek ----
    log_ids = [log.id for log in logs]
    feedbacks = (
        db.query(QuestionFeedback)
        .filter(QuestionFeedback.question_log_id.in_(log_ids))
        .all()
    )
    feedback_by_log_id = {fb.question_log_id: fb for fb in feedbacks}

    messages: list[ConversationMessageResponse] = []
    for log in logs:
        sources = [
            FatwaSource(
                id=str(fid),
                question=fatwa_by_id[str(fid)].question,
                answer=fatwa_by_id[str(fid)].answer,
                main_category=fatwa_by_id[str(fid)].main_category,
                source_dataset=fatwa_by_id[str(fid)].source_dataset,
                source_url=fatwa_by_id[str(fid)].source_url,
            )
            for fid in (log.retrieved_fatwa_ids or [])
            if str(fid) in fatwa_by_id
        ]

        feedback = feedback_by_log_id.get(log.id)

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


async def get_conversation_messages(
    conversation_id: uuid.UUID, user_id: uuid.UUID, db: Session
) -> list[ConversationMessageResponse]:
    """Eski, sayfalamasız uç nokta — artık route'ta kullanılmıyor, geriye dönük referans için tutuluyor."""
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
    return _build_message_responses(logs, db)


async def get_messages_page(
    db: Session,
    conversation_id: str,
    user_id: str,
    limit: int,
    before: Optional[str],
) -> ConversationMessagesPage:
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail=ResponseSignal.CONVERSATION_NOT_FOUND.value)
    if str(conversation.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail=ResponseSignal.CONVERSATION_FORBIDDEN.value)

    query = db.query(QuestionLog).filter(QuestionLog.conversation_id == conversation_id)

    if before:
        try:
            created_at_str, cursor_log_id = before.split("|", 1)
            before_created_at = datetime.fromisoformat(created_at_str)
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail=ResponseSignal.INVALID_CURSOR.value)

        # (created_at, id) satır karşılaştırması: aynı milisaniyede birden
        # fazla kayıt olsa bile atlama/mükerrer riski olmadan "bundan öncekiler".
        query = query.filter(
            tuple_(QuestionLog.created_at, QuestionLog.id) < (before_created_at, cursor_log_id)
        )

    # has_more'u ekstra count sorgusu atmadan anlamak için limit+1 çekiyoruz.
    rows = (
        query.order_by(QuestionLog.created_at.desc(), QuestionLog.id.desc())
        .limit(limit + 1)
        .all()
    )

    has_more = len(rows) > limit
    page_rows = rows[:limit]
    page_rows.reverse()  # sayfa içinde kronolojik sıraya (eski -> yeni) çevir

    next_cursor = None
    if has_more and page_rows:
        oldest = page_rows[0]
        next_cursor = f"{oldest.created_at.isoformat()}|{oldest.id}"

    items = _build_message_responses(page_rows, db)

    return ConversationMessagesPage(items=items, has_more=has_more, next_cursor=next_cursor)