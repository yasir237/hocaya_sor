"""
assets/fatwas/ altındaki iki JSON dosyasını okuyup 'fatwas' tablosuna yükler.
Embedding alanı bu aşamada doldurulmaz (None bırakılır) -- ayrı bir script
ile sonra doldurulacak.

Çalıştırma:
    cd src
    python -m scripts.load_fatwas
(ya da dosyayı src/ içine koyup `python load_fatwas.py` ile çalıştır)
"""

import json
import re
import sys
import os
import uuid
from datetime import datetime

sys.path.append(os.path.dirname(__file__))

from models.db_connection import SessionLocal
from models.db_schemes.hocaya_sor.schemes.fatwa import Fatwa


ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets", "fatwas")
FETVALAR_PATH = os.path.join(ASSETS_DIR, "fetvalar.jsonl")
PDF_FETVALAR_PATH = os.path.join(ASSETS_DIR, "pdf_fetvalar.json")

# PDF'den çıkmış metinlerdeki sayfa-no + form-feed + başlık kalıntısı deseni.
# Örnek kirlilik: "52  \fİTİKAD" veya "53  \fDİN İŞLERİ YÜKSEK KURULU FETVALARI"
PDF_NOISE_PATTERN = re.compile(r"\d+\s*\x0c[^\n]*")


def clean_pdf_text(text: str) -> str:
    if not text:
        return text
    cleaned = PDF_NOISE_PATTERN.sub(" ", text)
    # birden fazla boşluğu teke indir
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def parse_date(date_str: str | None):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def load_fetvalar_jsonl(path: str, source_dataset: str) -> list[dict]:
    """fetvalar.json -- her satır ayrı bir JSON objesi (JSONL)."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  [UYARI] {path} satır {line_num} parse edilemedi: {e}")
                continue
            obj["source_dataset"] = source_dataset
            records.append(obj)
    return records


def load_pdf_fetvalar_json(path: str, source_dataset: str) -> list[dict]:
    """pdf_fetvalar.json -- normal JSON array."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for obj in data:
        obj["answer"] = clean_pdf_text(obj.get("answer", ""))
        obj["question"] = clean_pdf_text(obj.get("question", ""))
        obj["source_dataset"] = source_dataset
    return data


def upsert_fatwa(db, record: dict) -> str:
    """
    Kayıt zaten varsa atla, yoksa ekle.
    Dönüş: 'inserted' | 'skipped' | 'error'
    """
    raw_id = record.get("id")
    if not raw_id:
        return "error"

    try:
        fatwa_id = raw_id if isinstance(raw_id, uuid.UUID) else uuid.UUID(str(raw_id))
    except (ValueError, AttributeError):
        return "error"

    existing = db.get(Fatwa, fatwa_id)
    if existing is not None:
        return "skipped"

    fatwa = Fatwa(
        id=fatwa_id,
        question=record.get("question", ""),
        answer=record.get("answer", ""),
        main_category=record.get("main_category") or "Bilinmiyor",
        sub_category=record.get("sub_category"),
        date=parse_date(record.get("date")),
        date_raw=record.get("date_raw"),
        source_url=record.get("source_url"),
        status=record.get("status", "active"),
        source_dataset=record["source_dataset"],
        embedding=None,
    )
    db.add(fatwa)
    return "inserted"


def main():
    print("Fetva yükleme başlıyor...\n")

    all_records = []

    if os.path.exists(FETVALAR_PATH):
        recs = load_fetvalar_jsonl(FETVALAR_PATH, source_dataset="fetvalar")
        print(f"fetvalar.json -> {len(recs)} kayıt okundu")
        all_records.extend(recs)
    else:
        print(f"[UYARI] {FETVALAR_PATH} bulunamadı, atlanıyor.")

    if os.path.exists(PDF_FETVALAR_PATH):
        recs = load_pdf_fetvalar_json(PDF_FETVALAR_PATH, source_dataset="pdf_fetvalar")
        print(f"pdf_fetvalar.json -> {len(recs)} kayıt okundu (temizlendi)")
        all_records.extend(recs)
    else:
        print(f"[UYARI] {PDF_FETVALAR_PATH} bulunamadı, atlanıyor.")

    print(f"\nToplam {len(all_records)} kayıt işlenecek.\n")

    db = SessionLocal()
    inserted = skipped = errors = 0

    try:
        for i, record in enumerate(all_records, start=1):
            result = upsert_fatwa(db, record)
            if result == "inserted":
                inserted += 1
            elif result == "skipped":
                skipped += 1
            else:
                errors += 1
                print(f"  [HATA] kayıt işlenemedi (id eksik?): {record.get('question', '???')[:50]}")

            # 200 kayıtta bir commit -- tek seferde dev bir transaction açmamak için
            if i % 200 == 0:
                db.commit()
                print(f"  ... {i}/{len(all_records)} işlendi (commit edildi)")

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"\n[KRİTİK HATA] İşlem geri alındı: {e}")
        raise
    finally:
        db.close()

    print("\n--- ÖZET ---")
    print(f"Eklenen : {inserted}")
    print(f"Atlanan (zaten vardı) : {skipped}")
    print(f"Hatalı  : {errors}")


if __name__ == "__main__":
    main()