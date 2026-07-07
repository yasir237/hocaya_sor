"""
assets/fatwas/islamweb_fetvalar.json (ham) -> normalize edilmiş JSON array üretir.

Ham dosyadaki id sorunları:
  - Bazı id'ler UUID değil ("islamweb-1360", "58889", "6707-2" gibi)
  - Bazı kayıtlarda id alanı hiç yok

Bu script, geçerli bir UUID olmayan/olmayan her id için
source_url + question alanlarından DETERMİNİSTİK bir UUID5 üretir.
Aynı girdiyle tekrar çalıştırıldığında aynı UUID'yi üretir (idempotent),
böylece load_fatwas.py'deki upsert mantığı bozulmaz.

Kullanım:
    python normalize_islamweb.py <ham_dosya.json> <çıktı_dosyası.json>
"""

import json
import sys
import uuid

# Sabit bir namespace -- proje için tek sefer üretilip sabitlenmeli.
# (Rastgele değil, sabit olması önemli: her çalıştırmada aynı sonucu vermeli.)
ISLAMWEB_NAMESPACE = uuid.UUID("6f2a1e2e-6b34-4c1a-9d2a-a1b2c3d4e5f6")


def is_valid_uuid(value) -> bool:
    if isinstance(value, uuid.UUID):
        return True
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def resolve_id(record: dict) -> tuple[str, str]:
    """
    Dönüş: (final_id_str, kaynak)
    kaynak: 'original' | 'derived'
    """
    raw_id = record.get("id")
    if raw_id and is_valid_uuid(raw_id):
        return str(raw_id), "original"

    # id yok ya da geçersiz -> source_url + question'dan deterministik üret
    source_url = (record.get("source_url") or "").strip()
    question = (record.get("question") or "").strip()

    if not source_url and not question:
        # Hiçbir ayırt edici alan yoksa üretilen id her kayıt için aynı olur
        # ve çakışıp birbirini ezer -- bu durumu ayrıca raporluyoruz.
        raise ValueError("Ne id, ne source_url, ne de question var -- kayıt ayırt edilemiyor")

    name = f"{source_url}|{question}"
    derived = uuid.uuid5(ISLAMWEB_NAMESPACE, name)
    return str(derived), "derived"


def main():
    if len(sys.argv) != 3:
        print("Kullanım: python normalize_islamweb.py <ham_dosya.json> <çıktı_dosyası.json>")
        sys.exit(1)

    in_path, out_path = sys.argv[1], sys.argv[2]

    with open(in_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"{len(records)} kayıt okundu.\n")

    normalized = []
    seen_ids = {}
    stats = {"original": 0, "derived": 0, "errors": 0, "collisions": 0}

    for i, record in enumerate(records):
        try:
            final_id, source = resolve_id(record)
        except ValueError as e:
            stats["errors"] += 1
            print(f"  [HATA] kayıt {i}: {e} -- soru: {record.get('question', '???')[:50]}")
            continue

        if final_id in seen_ids:
            stats["collisions"] += 1
            print(
                f"  [ÇAKIŞMA] kayıt {i}, id={final_id} zaten kayıt {seen_ids[final_id]}'te kullanılmış "
                f"-- soru: {record.get('question', '???')[:50]}"
            )
            continue

        seen_ids[final_id] = i
        stats[source] += 1

        new_record = dict(record)
        new_record["id"] = final_id
        new_record["source_dataset"] = "islamweb"
        normalized.append(new_record)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)

    print("\n--- ÖZET ---")
    print(f"Orijinal (geçerli) id ile kalan : {stats['original']}")
    print(f"Türetilmiş (deterministik) id atanan : {stats['derived']}")
    print(f"Çakışma (atlanan) : {stats['collisions']}")
    print(f"Hata (atlanan) : {stats['errors']}")
    print(f"Toplam yazılan kayıt : {len(normalized)}")
    print(f"\nÇıktı: {out_path}")


if __name__ == "__main__":
    main()