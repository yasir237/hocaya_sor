"""
RAG arama kalitesini test eder.
Bir soru girildiğinde:
  1. Soruyu embed eder
  2. En yakın 5 fetvayı getirir
  3. Bunları context olarak LLM'e gönderip cevap üretir
  4. Hem bulunan fetvaları hem de üretilen cevabı ekrana yazar

Çalıştırma:
    cd src
    python test_rag.py
"""

import os
import sys

sys.path.append(os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory


SYSTEM_PROMPT = """Sen bir İslam hukuku (fıkıh) asistanısın. 
Sana verilen fetva metinlerine dayanarak kullanıcının sorusunu Türkçe olarak cevaplıyorsun.
Cevabın yalnızca verilen kaynaklara dayansın; kaynaklarda olmayan bir bilgiyi ekleme.
Cevabın sonunda hangi kaynaklardan yararlandığını kısaca belirt."""


def search_and_answer(question: str, top_k: int = 5):
    llm = LLMProviderFactory.create()
    vdb = VectorDBProviderFactory.create()

    print(f"\n{'='*60}")
    print(f"SORU: {question}")
    print(f"{'='*60}")

    # 1. Soruyu embed et
    print("\n[1] Soru embed ediliyor...")
    query_vector = llm.embed_text(question)

    # 2. En yakın fetvaları bul
    print(f"[2] En yakın {top_k} fetva aranıyor...")
    results = vdb.search(query_vector, top_k=top_k)

    print(f"\n--- BULUNAN FETVALAR ({len(results)} adet) ---")
    for i, r in enumerate(results, 1):
        print(f"\n[{i}] Kategori: {r['main_category']} | Kaynak: {r['source_dataset']}")
        print(f"    Soru : {r['question'][:100]}{'...' if len(r['question']) > 100 else ''}")
        print(f"    Cevap: {r['answer'][:200]}{'...' if len(r['answer']) > 200 else ''}")

    # 3. LLM ile cevap üret
    print("\n[3] LLM cevabı üretiyor...")
    context = "\n\n".join(
        f"Fetva {i+1}:\nSoru: {r['question']}\nCevap: {r['answer']}"
        for i, r in enumerate(results)
    )
    prompt = f"""Aşağıdaki fetva metinlerine dayanarak soruyu cevapla.

FETVALAR:
{context}

KULLANICI SORUSU: {question}"""

    answer = llm.generate_text(prompt, system_prompt=SYSTEM_PROMPT)

    print(f"\n--- ÜRETİLEN CEVAP ---")
    print(answer)
    print(f"{'='*60}\n")


def main():
    test_sorular = [
        "Sakal tıraşı büyük günah mıdır?",
        "Hicap zorla giydirilirse hükmü değişir mi?",
        "Hırsızlık haddi için nisab şartı nedir?",
    ]

    for soru in test_sorular:
        search_and_answer(soru)
        input("\nDevam etmek için Enter'a bas...")


if __name__ == "__main__":
    main()