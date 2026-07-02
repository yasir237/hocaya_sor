"""
VectorDB sağlayıcıları için soyut arayüz. Şu an tek implementasyonumuz
pgvector (zaten Postgres'i RAG verisiyle birlikte kullanıyoruz), ama ileride
Qdrant / Pinecone / Weaviate gibi ayrı bir vector DB'ye geçmek istersen
sadece yeni bir provider yazman yeterli olacak.
"""

from abc import ABC, abstractmethod


class VectorDBInterface(ABC):

    @abstractmethod
    def insert_vector(self, record_id: str, vector: list[float]) -> None:
        """Var olan bir kaydın embedding'ini günceller / ekler."""
        pass

    @abstractmethod
    def search(self, query_vector: list[float], top_k: int = 5) -> list[dict]:
        """
        En yakın top_k kaydı döner.
        Dönüş formatı: [{"id": ..., "question": ..., "answer": ..., "score": ...}, ...]
        """
        pass