"""
Fetva arama ve cevap üretme iş mantığı.
"""

import datetime
import logging
import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session

from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory
from models.schemas.fatwa_schemas import (
    AskRequest, AskResponse, FatwaSource, FeedbackRequest, FeedbackResponse,
)
from models.db_schemes.hocaya_sor.schemes.question_log import QuestionLog
from models.db_schemes.hocaya_sor.schemes.question_feedback import QuestionFeedback
from models.db_schemes.hocaya_sor.schemes.conversation import Conversation
from models.enums.ResponseEnums import ResponseSignal

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Sen Diyanet İşleri Başkanlığı'nın fetva veritabanına dayanan bir İslam hukuku asistanısın.

GÖREVIN:
Kullanıcının sorusunu, sana verilen fetva metinlerine dayanarak sade ve anlaşılır Türkçeyle cevapla.
Her kesimden insanın anlayabileceği bir dil kullan; gereksiz teknik terim kullanma, kullanmak zorundaysan kısa bir parantez içi açıklama ekle.

CEVAP KURALLARI:
1. Yalnızca verilen fetva metinlerine dayan. Kaynaklarda olmayan bilgiyi kesinlikle ekleme.
2. Soru kısa ve net bir cevap gerektiriyorsa tek paragrafla bitir. Birden fazla durum veya senaryo varsa madde madde açıkla.
3. Fetva metinlerini olduğu gibi kopyalama; kendi cümtelerinle, sade bir dille özetle ve açıkla.
4. Farklı görüşler veya mezhepler arasında fark varsa bunu açıkça belirt.
5. Cevabın sonuna "Kaynaklar:" başlığı altında yararlandığın fetvaların URL'lerini listele.
   URL yoksa o kaynağı kaynak listesine ekleme.

KAYNAK GÖSTERIM FORMATI:
Kaynaklar:
- <URL>
- <URL>
"""


_embedding_llm = None
_generation_llm = None
_vdb = None


def get_embedding_llm():
    global _embedding_llm
    if _embedding_llm is None:
        _embedding_llm = LLMProviderFactory.create_embedding_provider()
    return _embedding_llm


def get_generation_llm():
    global _generation_llm
    if _generation_llm is None:
        _generation_llm = LLMProviderFactory.create_generation_provider()
    return _generation_llm


def get_vdb():
    global _vdb
    if _vdb is None:
        _vdb = VectorDBProviderFactory.create()
    return _vdb


def _make_conversation_title(question: str) -> str:
    title = question.strip()
    return title[:60] + ("…" if len(title) > 60 else "")


async def ask_question(request: AskRequest, user_id: uuid.UUID, db: Session) -> AskResponse:
    embedding_llm = get_embedding_llm()
    generation_llm = get_generation_llm()
    vdb = get_vdb()

    # Sohbeti bul (mevcutsa) ya da oluştur (yoksa) — henüz commit etmiyoruz,
    # asıl soru-cevap işlemiyle birlikte tek transaction'da tamamlanacak.
    if request.conversation_id is not None:
        conversation = (
            db.query(Conversation).filter(Conversation.id == request.conversation_id).first()
        )
        if conversation is None or conversation.user_id != user_id:
            raise HTTPException(
                status_code=404, detail=ResponseSignal.CONVERSATION_NOT_FOUND.value
            )
    else:
        conversation = Conversation(
            user_id=user_id,
            title=_make_conversation_title(request.question),
        )
        db.add(conversation)
        db.flush()  # commit beklemeden conversation.id'yi almak için

    try:
        query_vector = embedding_llm.embed_text(request.question)
    except Exception:
        logger.exception("Embedding servisi hatası (user_id=%s)", user_id)
        raise HTTPException(
            status_code=503,
            detail=ResponseSignal.EMBEDDING_SERVICE_ERROR.value,
        )

    try:
        results = vdb.search(query_vector, top_k=request.top_k)
    except Exception:
        logger.exception("Vektör veritabanı arama hatası (user_id=%s)", user_id)
        raise HTTPException(
            status_code=503,
            detail=ResponseSignal.VECTORDB_SERVICE_ERROR.value,
        )

    if not results:
        raise HTTPException(status_code=404, detail=ResponseSignal.FATWA_NOT_FOUND.value)

    context_parts = []
    for i, r in enumerate(results):
        url_line = f"Kaynak URL: {r['source_url']}" if r.get("source_url") else "Kaynak URL: yok"
        context_parts.append(
            f"Fetva {i+1}:\nSoru: {r['question']}\nCevap: {r['answer']}\n{url_line}"
        )
    context = "\n\n".join(context_parts)

    prompt = f"""Aşağıdaki fetva metinlerine dayanarak soruyu cevapla.

FETVALAR:
{context}

KULLANICI SORUSU: {request.question}"""

    try:
        answer = generation_llm.generate_text(prompt, system_prompt=SYSTEM_PROMPT)
    except Exception:
        logger.exception("Cevap üretme hatası (user_id=%s)", user_id)
        raise HTTPException(
            status_code=503,
            detail=ResponseSignal.GENERATION_SERVICE_ERROR.value,
        )

    # Soruyu logla (kullanıcı, sohbet, cevap, kullanılan fetva id'leri)
    try:
        log = QuestionLog(
            user_id=user_id,
            conversation_id=conversation.id,
            question=request.question,
            answer=answer,
            retrieved_fatwa_ids=[uuid.UUID(r["id"]) for r in results],
        )
        conversation.updated_at = datetime.datetime.now(datetime.timezone.utc)
        db.add(log)
        db.commit()
        db.refresh(log)
    except Exception:
        db.rollback()
        logger.exception("Soru loglama hatası (user_id=%s)", user_id)
        # Loglama başarısız olsa da kullanıcı cevabı almalı; log_id olmadan devam et
        # yerine burada isteği tamamen düşürmek yanlış olur, ama log_id gerekli
        # olduğu için genel bir hata dönmek daha tutarlı.
        raise HTTPException(
            status_code=500,
            detail=ResponseSignal.SERVER_ERROR.value,
        )

    return AskResponse(
        conversation_id=conversation.id,
        log_id=log.id,
        question=request.question,
        answer=answer,
        sources=[
            FatwaSource(
                id=r["id"],
                question=r["question"],
                answer=r["answer"],
                main_category=r["main_category"],
                source_dataset=r["source_dataset"],
                source_url=r.get("source_url"),
            )
            for r in results
        ],
    )

async def submit_feedback(
    log_id: uuid.UUID, request: FeedbackRequest, user_id: uuid.UUID, db: Session
) -> FeedbackResponse:
    log = db.query(QuestionLog).filter(QuestionLog.id == log_id).first()
    if log is None:
        raise HTTPException(status_code=404, detail=ResponseSignal.QUESTION_LOG_NOT_FOUND.value)
    if log.user_id != user_id:
        raise HTTPException(status_code=403, detail=ResponseSignal.FEEDBACK_FORBIDDEN.value)

    try:
        existing = db.query(QuestionFeedback).filter(
            QuestionFeedback.question_log_id == log_id
        ).first()

        if existing:
            existing.feedback = request.feedback.value
            existing.comment = request.comment
            db.commit()
            db.refresh(existing)
            fb = existing
        else:
            fb = QuestionFeedback(
                question_log_id=log_id,
                user_id=user_id,
                feedback=request.feedback.value,
                comment=request.comment,
            )
            db.add(fb)
            db.commit()
            db.refresh(fb)
    except Exception:
        db.rollback()
        logger.exception("Feedback kaydetme hatası (user_id=%s, log_id=%s)", user_id, log_id)
        raise HTTPException(
            status_code=500,
            detail=ResponseSignal.SERVER_ERROR.value,
        )

    return FeedbackResponse(
        question_log_id=fb.question_log_id,
        feedback=fb.feedback,
        comment=fb.comment,
    )