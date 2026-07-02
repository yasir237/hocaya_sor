"""
Fetva arama ve cevap üretme iş mantığı.
"""

from fastapi import HTTPException

from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory
from models.schemas.fatwa_schemas import AskRequest, AskResponse, FatwaSource


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


_llm = None
_vdb = None


def get_llm():
    global _llm
    if _llm is None:
        _llm = LLMProviderFactory.create()
    return _llm


def get_vdb():
    global _vdb
    if _vdb is None:
        _vdb = VectorDBProviderFactory.create()
    return _vdb


async def ask_question(request: AskRequest) -> AskResponse:
    llm = get_llm()
    vdb = get_vdb()

    # 1. Soruyu embed et
    try:
        query_vector = llm.embed_text(request.question)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Embedding servisi hatası: {str(e)}")

    # 2. En yakın fetvaları getir
    try:
        results = vdb.search(query_vector, top_k=request.top_k)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Veritabanı arama hatası: {str(e)}")

    if not results:
        raise HTTPException(status_code=404, detail="İlgili fetva bulunamadı.")

    # 3. Context oluştur — her fetvanın URL'sini de ekle ki LLM kaynak gösterebilsin
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

    # 4. LLM ile cevap üret
    try:
        answer = llm.generate_text(prompt, system_prompt=SYSTEM_PROMPT)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cevap üretme hatası: {str(e)}")

    return AskResponse(
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