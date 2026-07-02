"""
Tüm LLM / Embedding sağlayıcılarının uyması gereken soyut arayüz.
Provider değiştirmek istediğinde (Google -> Ollama -> OpenAI vs.)
sadece yeni bir provider sınıfı yazman ve factory'de kayıt etmen yeterli,
geri kalan kod (script'ler, route'lar) hiç değişmeden çalışmaya devam eder.
"""

from abc import ABC, abstractmethod


class LLMInterface(ABC):

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """
        Verilen metni embedding vektörüne çevirir.
        Dönüş: sabit boyutlu float listesi (örn. 768 boyut).
        """
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Birden fazla metni tek seferde embed eder (provider destekliyorsa
        gerçek batch API kullanır, desteklemiyorsa içeride sırayla embed_text çağırır).
        """
        pass

    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: str | None = None) -> str:
        """
        İleride RAG cevap üretme aşamasında kullanılacak.
        Şimdilik embedding script'i bunu çağırmıyor, ama interface'i
        baştan tanımlıyoruz ki LLM provider'ı da aynı factory ile yönetelim.
        """
        pass