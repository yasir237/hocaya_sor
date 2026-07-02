"""
Fetva arama ve cevap üretme iş mantığı.
"""

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


async def ask_question(request: AskRequest, user_id: uuid.UUID, db: Session) -> AskResponse:
    embedding_llm = get_embedding_llm()
    generation_llm = get_generation_llm()
    vdb = get_vdb()

    try:
        query_vector = embedding_llm.embed_text(request.question)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Embedding servisi hatası: {str(e)}")

    try:
        results = vdb.search(query_vector, top_k=request.top_k)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Veritabanı arama hatası: {str(e)}")

    if not results:
        raise HTTPException(status_code=404, detail="İlgili fetva bulunamadı.")

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
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cevap üretme hatası: {str(e)}")

    # Soruyu logla (kullanıcı, cevap, kullanılan fetva id'leri)
    log = QuestionLog(
        user_id=user_id,
        question=request.question,
        answer=answer,
        retrieved_fatwa_ids=[uuid.UUID(r["id"]) for r in results],
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return AskResponse(
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
        raise HTTPException(status_code=404, detail="Soru kaydı bulunamadı.")
    if log.user_id != user_id:
        raise HTTPException(status_code=403, detail="Bu soruya geri bildirim verme yetkiniz yok.")

    existing = db.query(QuestionFeedback).filter(
        QuestionFeedback.question_log_id == log_id
    ).first()

    if existing:
        existing.feedback = request.feedback.value
        db.commit()
        db.refresh(existing)
        fb = existing
    else:
        fb = QuestionFeedback(
            question_log_id=log_id,
            user_id=user_id,
            feedback=request.feedback.value,
        )
        db.add(fb)
        db.commit()
        db.refresh(fb)

    return FeedbackResponse(question_log_id=fb.question_log_id, feedback=fb.feedback)