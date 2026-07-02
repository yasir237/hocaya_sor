"""
pgvector (Postgres) tabanlı VectorDB provider.
"""

import uuid

from sqlalchemy import select

from stores.vectordb.VectorDBInterface import VectorDBInterface
from models.db_connection import SessionLocal
from models.db_schemes.hocaya_sor.schemes.fatwa import Fatwa


class PGVectorProvider(VectorDBInterface):

    def __init__(self, max_distance: float = 0.20):
        self.max_distance = max_distance

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

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        max_distance: float | None = None,
    ) -> list[dict]:
        """
        En yakın top_k fetvayı döner.
        max_distance eşiğini geçen (alakasız) sonuçlar filtrelenir.
        Cosine distance: 0 = aynı, 1 = ilgisiz, 2 = tamamen zıt.
        """
        threshold = max_distance if max_distance is not None else self.max_distance

        db = SessionLocal()
        try:
            distance_col = Fatwa.embedding.cosine_distance(query_vector).label("distance")
            stmt = (
                select(Fatwa, distance_col)
                .where(Fatwa.embedding.is_not(None))
                .where(distance_col <= threshold)
                .order_by(distance_col)
                .limit(top_k)
            )
            rows = db.execute(stmt).all()
            return [
                {
                    "id": str(r.Fatwa.id),
                    "question": r.Fatwa.question,
                    "answer": r.Fatwa.answer,
                    "main_category": r.Fatwa.main_category,
                    "source_dataset": r.Fatwa.source_dataset,
                    "source_url": r.Fatwa.source_url,
                    "distance": round(r.distance, 4),
                }
                for r in rows
            ]
        finally:
            db.close()