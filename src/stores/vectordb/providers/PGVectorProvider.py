"""
pgvector (Postgres) tabanlı VectorDB provider. Mevcut 'fatwas' tablosunu
hem ham veri hem de vektör deposu olarak kullanıyoruz -- ayrı bir vector DB
kurmaya gerek yok, pgvector extension'ı bunu zaten destekliyor.
"""

import uuid

from sqlalchemy import select

from stores.vectordb.VectorDBInterface import VectorDBInterface
from models.db_connection import SessionLocal
from models.db_schemes.hocaya_sor.schemes.fatwa import Fatwa


class PGVectorProvider(VectorDBInterface):

    def insert_vector(self, record_id: str, vector: list[float]) -> None:
        db = SessionLocal()
        try:
            fatwa_id = record_id if isinstance(record_id, uuid.UUID) else uuid.UUID(str(record_id))
            fatwa = db.get(Fatwa, fatwa_id)
            if fatwa is None:
                raise ValueError(f"id={record_id} ile kayıt bulunamadı.")
            fatwa.embedding = vector
            db.commit()
        finally:
            db.close()

    def search(self, query_vector: list[float], top_k: int = 5) -> list[dict]:
        db = SessionLocal()
        try:
            # pgvector'ın cosine distance operatörü: <=>
            # (Fatwa modelinde embedding kolonu Vector(768) tipinde tanımlı olduğu
            # için SQLAlchemy bu operatörü doğrudan destekler)
            stmt = (
                select(Fatwa)
                .where(Fatwa.embedding.is_not(None))
                .order_by(Fatwa.embedding.cosine_distance(query_vector))
                .limit(top_k)
            )
            results = db.execute(stmt).scalars().all()
            return [
                {
                    "id": str(r.id),
                    "question": r.question,
                    "answer": r.answer,
                    "main_category": r.main_category,
                    "source_dataset": r.source_dataset,
                }
                for r in results
            ]
        finally:
            db.close()