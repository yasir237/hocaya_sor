# 🕌 Hocaya Sor

**Diyanet İşleri Başkanlığı fetva veritabanına dayanan Türkçe İslam hukuku RAG sistemi.**

Kullanıcının sorduğu soruyu vektör aramasıyla ilgili fetvalarla eşleştirir, ardından büyük dil modeli aracılığıyla sade ve anlaşılır bir Türkçe cevap üretir. Tüm cevaplar kaynak URL'leriyle belgelenmiştir.

---

## 📑 İçindekiler

- [Özellikler](#-özellikler)
- [Mimari](#-mimari)
- [Teknoloji Yığını](#-teknoloji-yığını)
- [Kurulum](#-kurulum)
- [Yapılandırma](#-yapılandırma)
- [Veri Yükleme](#-veri-yükleme)
- [API Kullanımı](#-api-kullanımı)
- [Proje Yapısı](#-proje-yapısı)
- [Provider Değiştirme](#-provider-değiştirme)
- [Geliştirme](#-geliştirme)

---

## ✨ Özellikler

- 🔍 **Vektör tabanlı anlamsal arama** — kelime eşleşmesi değil, anlam benzerliği
- 🤖 **LLM destekli cevap üretimi** — bulunan fetvalar bağlam olarak kullanılır
- 🔗 **Kaynak şeffaflığı** — her cevap Diyanet fetva URL'leriyle belgelenmiştir
- 🔄 **Provider soyutlaması** — LLM ve VectorDB sağlayıcılarını tek satırla değiştirin
- 🚦 **Alakasız soru filtresi** — cosine distance eşiğiyle kapsam dışı sorular reddedilir
- ⚡ **Çoklu API key rotasyonu** — rate limit'e takılmadan 8'e kadar Google API key destekler
- 📄 **2393 fetva** — `fetvalar.json` ve `pdf_fetvalar.json` kaynaklarından derlenmiştir

---

## 🏗 Mimari

```
Kullanıcı Sorusu
      │
      ▼
┌─────────────────┐
│  FastAPI Route  │  POST /api/v1/fatwa/ask
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Controller   │  İş mantığı katmanı
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐  ┌──────────┐
│  LLM  │  │ VectorDB │
│Provider│  │ Provider │
└───┬───┘  └────┬─────┘
    │            │
    ▼            ▼
┌───────┐  ┌──────────────────┐
│Google │  │ PostgreSQL       │
│Gemini │  │ + pgvector       │
│ API   │  │ (2393 fetva,     │
│       │  │  3072 boyut)     │
└───────┘  └──────────────────┘
```

**Akış:**
1. Soru `gemini-embedding-001` ile 3072 boyutlu vektöre dönüştürülür
2. pgvector cosine distance ile en yakın fetvalar bulunur
3. Cosine distance > 0.20 ise `404` döner (kapsam dışı soru)
4. Bulunan fetvalar bağlam olarak `gemini-2.5-flash`'a gönderilir
5. LLM Türkçe, sade ve kaynaklı bir cevap üretir

---

## 🛠 Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| API | FastAPI |
| Veritabanı | PostgreSQL 16 + pgvector |
| ORM | SQLAlchemy 2.0 |
| Migration | Alembic |
| Embedding | Google `gemini-embedding-001` (3072 boyut) |
| LLM | Google `gemini-2.5-flash` |
| Container | Docker + Docker Compose |
| Python | 3.11 (Conda ortamı) |

---

## 🚀 Kurulum

### Gereksinimler

- Docker & Docker Compose
- Conda (ya da Python 3.11+)
- Google Gemini API key(ler)

### 1. Depoyu klonla

```bash
git clone https://github.com/kullanici/hocaya_sor.git
cd hocaya_sor
```

### 2. Conda ortamını oluştur

```bash
conda create -n hocaya_sor python=3.11 -y
conda activate hocaya_sor
pip install -r requirements.txt
```

### 3. Ortam dosyalarını yapılandır

```bash
cp src/.env.example src/.env
```

`.env` ve `docker/env/.env.postgres` dosyalarını düzenle (bkz. [Yapılandırma](#-yapılandırma)).

### 4. Veritabanını başlat

```bash
cd docker
docker compose up -d
docker exec -it hocaya_sor_pgvector psql -U hocaya_sor_user -d hocaya_sor_db \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 5. Migration'ları uygula

```bash
cd ../src
alembic -c alembic.ini upgrade head
```

### 6. Veriyi yükle ve embed et

```bash
# Fetvaları yükle (embedding olmadan)
python load_fatwas.py

# Embedding'leri doldur (~30-60 dakika, 8 API key ile daha hızlı)
python fill_embeddings.py
```

### 7. API'yi başlat

```bash
uvicorn main:app --reload --port 8000
```

API `http://localhost:8000` adresinde hazır. Swagger dokümantasyonu için `http://localhost:8000/docs`.

---

## ⚙️ Yapılandırma

### `src/.env`

```env
APP_NAME="hocaya_sor"
APP_VERSION="0.1"

# PostgreSQL
POSTGRES_USER=hocaya_sor_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=hocaya_sor_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5433

# LLM / Embedding
EMBEDDING_BACKEND=google
GOOGLE_API_KEYS=key1,key2,key3        # virgülle ayrılmış, rate limit için
GOOGLE_EMBEDDING_MODEL=gemini-embedding-001
GOOGLE_GENERATION_MODEL=gemini-2.5-flash
EMBEDDING_DIM=3072
EMBEDDING_SLEEP_SECONDS=0.1

# VectorDB
VECTORDB_BACKEND=pgvector
VECTOR_MAX_DISTANCE=0.20              # cosine eşiği (0=aynı, 1=ilgisiz)
```

### `docker/env/.env.postgres`

```env
POSTGRES_USER=hocaya_sor_user
POSTGRES_PASSWORD=your_password       # $ karakteri KULLANMAYIN (Docker interpolation)
POSTGRES_DB=hocaya_sor_db
```

> ⚠️ Docker Compose şifrelerdeki `$` karakterini ortam değişkeni olarak yorumlar. Şifrenizde `$` varsa ya `$$` olarak escape edin ya da `$` içermeyen bir şifre kullanın.

---

## 📦 Veri Yükleme

Fetva JSON dosyalarını `src/assets/fatwas/` altına yerleştirin:

| Dosya | Format | Kayıt |
|---|---|---|
| `fetvalar.json` | JSONL (satır başı JSON) | 1362 |
| `pdf_fetvalar.json` | JSON array | 1031 |

```bash
# Yükleme (idempotent — tekrar çalıştırılabilir)
python load_fatwas.py

# Embedding doldurma (kaldığı yerden devam eder)
python fill_embeddings.py
```

---

## 📡 API Kullanımı

### `POST /api/v1/fatwa/ask`

Kullanıcının sorusuna ilgili fetvalar bulunarak cevap üretilir.

**İstek:**

```bash
curl -X POST http://localhost:8000/api/v1/fatwa/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Faiz haram mı?", "top_k": 5}'
```

**Parametreler:**

| Alan | Tip | Varsayılan | Açıklama |
|---|---|---|---|
| `question` | string | — | Soru metni (3–1000 karakter) |
| `top_k` | integer | 5 | Kaç fetva baz alınsın (1–10) |

**Başarılı Yanıt (`200`):**

```json
{
  "question": "Faiz haram mı?",
  "answer": "Evet, İslam dinine göre faizin her çeşidi kesin olarak haramdır...\n\nKaynaklar:\n- https://kurul.diyanet.gov.tr/...",
  "sources": [
    {
      "id": "0193c42d-...",
      "question": "Bir kişinin malını faizli kredi ile satın almak isteyen kişiye satması caiz midir?",
      "answer": "İslam'a göre faizin her çeşidi haramdır...",
      "main_category": "TİCARÎ HAYAT",
      "source_dataset": "fetvalar",
      "source_url": "https://kurul.diyanet.gov.tr/tr/fetva/..."
    }
  ]
}
```

**Hata Yanıtları:**

| Kod | Açıklama |
|---|---|
| `404` | Kapsam dışı soru — ilgili fetva bulunamadı |
| `503` | Embedding veya LLM servis hatası |

---

## 📁 Proje Yapısı

```
hocaya_sor/
├── docker/
│   ├── docker-compose.yml
│   └── env/
│       └── .env.postgres
└── src/
    ├── main.py                          # FastAPI uygulaması
    ├── load_fatwas.py                   # Veri yükleme scripti
    ├── fill_embeddings.py               # Embedding doldurma scripti
    ├── test_rag.py                      # Terminal test scripti
    ├── assets/
    │   └── fatwas/                      # Ham JSON dosyaları
    ├── controllers/
    │   └── fatwa_controller.py          # İş mantığı
    ├── routes/
    │   └── fatwa_routes.py              # HTTP endpoint tanımları
    ├── models/
    │   ├── db_connection.py             # SQLAlchemy session
    │   ├── schemas/
    │   │   └── fatwa_schemas.py         # Pydantic request/response şemaları
    │   └── db_schemes/hocaya_sor/
    │       └── schemes/
    │           └── fatwa.py             # SQLAlchemy ORM modeli
    ├── stores/
    │   ├── llm/
    │   │   ├── LLMInterface.py          # Soyut LLM arayüzü
    │   │   ├── LLMProviderFactory.py    # Provider seçici
    │   │   └── providers/
    │   │       └── GoogleProvider.py    # Gemini implementasyonu
    │   └── vectordb/
    │       ├── VectorDBInterface.py     # Soyut VectorDB arayüzü
    │       ├── VectorDBProviderFactory.py
    │       └── providers/
    │           └── PGVectorProvider.py  # pgvector implementasyonu
    └── helpers/
        └── config.py                    # Pydantic Settings
```

---

## 🔄 Provider Değiştirme

Sistem provider soyutlamasıyla tasarlanmıştır. Sağlayıcıyı değiştirmek için:

**LLM / Embedding değiştirme (Google → Ollama):**

```env
# src/.env
EMBEDDING_BACKEND=ollama
```

```python
# stores/llm/providers/OllamaProvider.py oluştur, LLMInterface'i implemente et
# stores/llm/LLMProviderFactory.py içine elif backend == "ollama" ekle
```

**VectorDB değiştirme (pgvector → Qdrant):**

```env
# src/.env
VECTORDB_BACKEND=qdrant
```

```python
# stores/vectordb/providers/QdrantProvider.py oluştur, VectorDBInterface'i implemente et
# stores/vectordb/VectorDBProviderFactory.py içine elif backend == "qdrant" ekle
```

---

## 🧑‍💻 Geliştirme

### Yeni migration oluşturma

```bash
cd src
alembic -c alembic.ini revision --autogenerate -m "açıklama"
# Oluşan dosyaya import pgvector.sqlalchemy ekle (autogenerate eklemez)
alembic -c alembic.ini upgrade head
```

### Arama kalitesini test etme

```bash
cd src
python test_rag.py
```

### Cosine distance eşiğini ayarlama

```env
# src/.env — değeri küçültmek daha katı, büyütmek daha esnek filtre yapar
VECTOR_MAX_DISTANCE=0.20
```

---

## 📜 Lisans

Apache-2.0 license