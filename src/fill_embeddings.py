"""
fatwas tablosunda embedding IS NULL olan kayıtları bulup, question+answer
metnini LLMProviderFactory üzerinden embed eder ve tabloya yazar.

Idempotent: script kesilirse / tekrar çalıştırılırsa, zaten embed edilmiş
kayıtlar (embedding IS NOT NULL) bir daha işlenmez, kaldığı yerden devam eder.

Çalıştırma:
    cd src
    python fill_embeddings.py
"""

import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select

from models.db_connection import SessionLocal
from models.db_schemes.hocaya_sor.schemes.fatwa import Fatwa
from stores.llm.LLMProviderFactory import LLMProviderFactory


# her N kayıtta bir commit + ekrana ilerleme yazdır
COMMIT_EVERY = 50
# her embed isteği arasında küçük bir bekleme -- rate limit'e nazik davranmak için.
# 8 key round-robin yaptığımız için bunu çok küçük tutabiliyoruz.
SLEEP_BETWEEN_CALLS = float(os.getenv("EMBEDDING_SLEEP_SECONDS", "0.1"))


def build_embedding_text(fatwa: Fatwa) -> str:
    """Soru ve cevabı birleştirip tek bir metin olarak embed edeceğiz."""
    question = (fatwa.question or "").strip()
    answer = (fatwa.answer or "").strip()
    return f"Soru: {question}\nCevap: {answer}"


def main():
    llm = LLMProviderFactory.create()

    db = SessionLocal()
    try:
        # toplam kaç kayıt embed bekliyor, baştan göster
        total_pending = db.execute(
            select(Fatwa).where(Fatwa.embedding.is_(None))
        ).scalars().all()
        total = len(total_pending)
        print(f"Embedding bekleyen kayıt sayısı: {total}\n")

        if total == 0:
            print("Tüm kayıtlar zaten embed edilmiş, yapılacak iş yok.")
            return

        done = 0
        errors = 0

        for fatwa in total_pending:
            text = build_embedding_text(fatwa)
            try:
                vector = llm.embed_text(text)
                fatwa.embedding = vector
                done += 1
            except Exception as e:
                errors += 1
                print(f"  [HATA] id={fatwa.id} embed edilemedi: {e}")

            if (done + errors) % COMMIT_EVERY == 0:
                db.commit()
                print(f"  ... {done + errors}/{total} işlendi (commit edildi, başarılı={done}, hatalı={errors})")

            time.sleep(SLEEP_BETWEEN_CALLS)

        db.commit()

    except KeyboardInterrupt:
        print("\nKullanıcı tarafından durduruldu, şimdiye kadarki ilerleme commit ediliyor...")
        db.commit()
    finally:
        db.close()

    print("\n--- ÖZET ---")
    print(f"Başarıyla embed edilen : {done}")
    print(f"Hatalı                 : {errors}")


if __name__ == "__main__":
    main()