# 🕌 Hocaya Sor

**Diyanet İşleri Başkanlığı ve islamweb.net fetva veritabanlarına dayanan Türkçe İslam hukuku RAG sistemi.**

Kullanıcının sorduğu soruyu vektör aramasıyla ilgili fetvalarla eşleştirir, ardından büyük dil modeli aracılığıyla sade ve anlaşılır bir Türkçe cevap üretir. Tüm cevaplar kaynak URL'leriyle belgelenmiştir. Sorular otomatik olarak sohbetler (conversations) halinde gruplanır, geri bildirimler (like/dislike) loglanır; sisteme JWT tabanlı kullanıcı hesabı, e-posta doğrulama, access/refresh token akışı, profil yönetimi ve kimlik doğrulaması eklenmiştir.

---

## 📑 İçindekiler

- [Özellikler](#-özellikler)
- [Mimari](#-mimari)
- [Teknoloji Yığını](#-teknoloji-yığını)
- [Kurulum](#-kurulum)
- [Yapılandırma](#️-yapılandırma)
- [Veri Yükleme](#-veri-yükleme)
- [API Kullanımı](#-api-kullanımı)
- [Güvenlik](#-güvenlik)
- [Proje Yapısı](#-proje-yapısı)
- [Enum Yapısı](#-enum-yapısı)
- [Provider Değiştirme](#-provider-değiştirme)
- [Geliştirme](#-geliştirme)

---

## ✨ Özellikler

- 🔍 **Vektör tabanlı anlamsal arama** — kelime eşleşmesi değil, anlam benzerliği
- 🤖 **LLM destekli cevap üretimi** — bulunan fetvalar bağlam olarak kullanılır
- 🔗 **Kaynak şeffaflığı** — her cevap Diyanet fetva URL'leriyle belgelenmiştir
- 🔄 **Provider soyutlaması** — LLM ve VectorDB sağlayıcılarını `.env`'den tek satırla değiştirin (enum ile doğrulanır)
- 🚦 **Alakasız soru filtresi** — cosine distance eşiğiyle kapsam dışı sorular reddedilir
- ⚡ **Çoklu API key rotasyonu** — rate limit'e takılmadan 8'e kadar Google API key destekler
- 🔐 **JWT tabanlı kimlik doğrulama** — kayıt/giriş, bcrypt şifre hashleme
- 📧 **E-posta doğrulama** — kayıt sonrası Resend üzerinden 6 haneli kod gönderilir; hesap doğrulanmadan giriş yapılamaz. Kod süresi dolarsa veya bulunamazsa yeniden gönderim istenebilir
- ♻️ **Access + Refresh token akışı** — kısa ömürlü access token (30 dk), uzun ömürlü refresh token (30 gün, DB'de hash'li) ve logout ile iptal (revoke) mekanizması
- 👤 **Profil yönetimi** — kullanıcı kendi ad/e-posta bilgisini görüntüleyebilir, adını güncelleyebilir
- 💬 **Sohbet geçmişi (conversations)** — sorular tek tek değil, birbirine bağlı sohbetler halinde gruplanır; kullanıcı geçmiş sohbetlerini listeleyip mesaj geçmişini geri yükleyebilir
- 📝 **Soru loglama** — her soru, cevap, hangi sohbete ait olduğu ve kullanılan fetva id'leri `question_logs` tablosunda tutulur
- 👍👎 **Like/Dislike geri bildirimi** — her soruya bağımsız olarak feedback verilebilir, ayrı `question_feedbacks` tablosunda tutulur
- 🛡 **API rate limiting** — auth, fetva ve profil endpoint'leri IP bazlı istek limitine sahiptir
- 🧩 **Merkezi enum yapısı** — backend seçimleri, feedback tipi ve tüm hata/başarı mesajları `models/enums/` altında tek kaynaktan yönetilir
- 📄 **2488 fetva** — `fetvalar.json` (Diyanet), `pdf_fetvalar.json` (Diyanet) ve `islamweb_fetvalar.json` (islamweb.net) kaynaklarından derlenmiştir

---

## 🏗 Mimari

```
Kullanıcı
   │
   ├── POST /api/v1/auth/register  (rate limit: 5/dk)
   │       → hesap oluşturulur (is_verified=False)
   │       → Resend ile 6 haneli doğrulama kodu e-postayla gönderilir
   │       → access_token + refresh_token döner (fatwa endpoint'leri için
   │         hesabın doğrulanmış olması gerekir, bkz. aşağıdaki not)
   │
   ├── POST /api/v1/auth/verify-email  (rate limit: 10/dk)
   │       → e-posta + 6 haneli kod ile hesabı doğrular (is_verified=True)
   │
   ├── POST /api/v1/auth/resend-verification  (rate limit: 3/dk)
   │       → kod süresi dolmuş/kaybolmuşsa yeni bir doğrulama kodu gönderir
   │
   ├── POST /api/v1/auth/login  (rate limit: 5/dk)
   │       → is_verified=False ise 403 (EMAIL_NOT_VERIFIED) döner
   │       → is_verified=True ise access_token (30 dk) + refresh_token (30 gün, DB'de hash'li)
   │
   ├── POST /api/v1/auth/refresh (rate limit: 20/dk)
   │       → refresh_token karşılığında yeni access_token
   │
   ├── POST /api/v1/auth/logout (rate limit: 10/dk)
   │       → refresh_token'ı DB'de iptal eder (revoked_at)
   │
   ├── GET  /api/v1/auth/me
   │       → giriş yapmış kullanıcının profil bilgisini döner (ad, e-posta)
   │
   ├── PATCH /api/v1/auth/me (rate limit: 3/dk)
   │       → kullanıcının adını günceller
   │
   ▼ (access_token ile)
┌──────────────────┐
│   FastAPI Route  │  POST /api/v1/fatwa/ask  (rate limit: 10/dk)
└────────┬─────────┘
         │  conversation_id verilmişse mevcut sohbete eklenir,
         │  verilmemişse otomatik yeni bir sohbet açılır
         ▼
┌──────────────────┐
│     Controller    │  İş mantığı katmanı
└────────┬──────────┘
         │
    ┌────┴────┬─────────────┬───────────────┐
    ▼         ▼             ▼               ▼
┌───────┐ ┌──────────┐ ┌──────────────┐ ┌───────────────┐
│  LLM  │ │ VectorDB │ │ question_logs│ │ conversations  │
│Provider│ │ Provider │ │  (log_id)    │ │ (conversation_ │
└───┬───┘ └────┬─────┘ └──────────────┘ │  id, title)    │
    │           │                        └───────────────┘
    ▼           ▼
┌───────┐ ┌──────────────────┐
│Google/│ │ PostgreSQL       │
│ Groq  │ │ + pgvector       │
│ API   │ │ (2488 fetva,     │
│       │ │  3072 boyut)     │
└───────┘ └──────────────────┘

Kullanıcı → POST /api/v1/fatwa/feedback/{log_id} (rate limit: 30/dk)
             → question_feedbacks tablosuna like/dislike (upsert)

Kullanıcı → GET /api/v1/conversations
             → kullanıcının tüm sohbetlerini (başlık + tarih) listeler
Kullanıcı → GET /api/v1/conversations/{conversation_id}/messages
             → o sohbetteki tüm soru-cevapları (kaynak ve feedback dahil) döner
```

**Akış:**
1. Kullanıcı `/api/v1/auth/register` ile kayıt olur; hesap `is_verified=False` olarak oluşturulur ve Resend üzerinden e-posta adresine 6 haneli bir doğrulama kodu gönderilir
2. Kullanıcı `/api/v1/auth/verify-email` ile kodu girerek hesabını doğrular (`is_verified=True`)
3. Kod süresi dolduysa veya e-posta hiç ulaşmadıysa `/api/v1/auth/resend-verification` ile yeni bir kod istenebilir
4. Doğrulanmış bir hesapla `/api/v1/auth/login` ile giriş yapılır; bir **access token** (30 dakika geçerli) ve bir **refresh token** (30 gün geçerli, veritabanında yalnızca hash'i tutulur) alınır. Hesap henüz doğrulanmadıysa login `403 EMAIL_NOT_VERIFIED` ile reddedilir
5. Access token süresi dolunca, kullanıcı tekrar login olmadan `/api/v1/auth/refresh` ile refresh token'ını kullanarak yeni bir access token alır
6. `/api/v1/auth/logout` çağrılırsa refresh token DB'de iptal edilir (`revoked_at` doldurulur); o refresh token bir daha yeni access token üretemez
7. Kullanıcı `/api/v1/auth/me` ile kendi profilini görüntüleyebilir, `PATCH` ile adını güncelleyebilir
8. Soru sorulurken istek gövdesinde `conversation_id` gönderilirse o sohbete eklenir; gönderilmezse ilk sorudan otomatik türetilen bir başlıkla yeni bir sohbet açılır ve `conversation_id` yanıtta döner
9. Soru `gemini-embedding-001` ile 3072 boyutlu vektöre dönüştürülür
10. pgvector cosine distance ile en yakın fetvalar bulunur
11. Cosine distance > 0.20 ise `404` döner (kapsam dışı soru)
12. Bulunan fetvalar bağlam olarak LLM'e (Gemini veya Groq — `.env`'deki `GENERATION_BACKEND`'e göre) gönderilir
13. LLM Türkçe, sade ve kaynaklı bir cevap üretir
14. Soru, cevap, hangi sohbete ait olduğu ve kullanılan fetva id'leri `question_logs`'a otomatik kaydedilir; dönen `log_id` ile kullanıcı isteğe bağlı like/dislike geri bildirimi verebilir
15. Kullanıcı `/api/v1/conversations` ile geçmiş sohbetlerini listeleyebilir, `/api/v1/conversations/{id}/messages` ile bir sohbetin tüm geçmişini geri yükleyebilir

---

## 🛠 Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| API | FastAPI |
| Veritabanı | PostgreSQL 16 + pgvector |
| ORM | SQLAlchemy 2.0 |
| Migration | Alembic |
| Embedding | Google `gemini-embedding-001` (3072 boyut) |
| LLM (generation) | Google `gemini-2.5-flash` veya Groq (`llama-3.3-70b` → fallback zinciri) |
| Auth | JWT access token (PyJWT) + opaque refresh token (DB'de sha256 hash) + bcrypt |
| E-posta | Resend (doğrulama kodu gönderimi) |
| Rate Limiting | slowapi |
| Container | Docker + Docker Compose |
| Python | 3.11 (Conda ortamı) |

---

## 🚀 Kurulum

### Gereksinimler

- Docker & Docker Compose
- Conda (ya da Python 3.11+)
- Google Gemini API key(ler) ve/veya Groq API key
- Resend API key (e-posta doğrulama için)

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

`.env` ve `docker/env/.env.postgres` dosyalarını düzenle (bkz. [Yapılandırma](#️-yapılandırma)).

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

# Embedding
EMBEDDING_BACKEND=google
GOOGLE_API_KEYS=key1,key2,key3        # virgülle ayrılmış, rate limit için
GOOGLE_EMBEDDING_MODEL=gemini-embedding-001
GOOGLE_GENERATION_MODEL=gemini-2.5-flash
EMBEDDING_DIM=3072
EMBEDDING_SLEEP_SECONDS=0.1

# Cevap üretimi (generation) — embedding'den bağımsız, "google" ya da "groq"
GENERATION_BACKEND=google
GROQ_API_KEY=
GROQ_GENERATION_MODEL=llama-3.3-70b-versatile

# VectorDB
VECTORDB_BACKEND=pgvector
VECTOR_MAX_DISTANCE=0.20              # cosine eşiği (0=aynı, 1=ilgisiz)

# JWT / Auth
JWT_SECRET_KEY=                       # en az 32 karakter, örn: openssl rand -hex 32
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRE_MINUTES=30          # access token ömrü
JWT_REFRESH_EXPIRE_DAYS=30            # refresh token ömrü

# E-posta doğrulama (Resend)
RESEND_API_KEY=                       # resend.com/api-keys üzerinden alınır
EMAIL_FROM=Hocaya Sor <onboarding@resend.dev>   # domain doğrulanana kadar Resend'in test adresi
EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES=15       # doğrulama kodunun geçerlilik süresi
```

> ⚠️ `JWT_SECRET_KEY` **en az 32 karakter** olmalı — uygulama başlarken bunu doğrular, kısa bir değer girilirse başlamayı reddeder. Üretmek için: `openssl rand -hex 32`. Production'da bu değer mutlaka gizli tutulmalı, `.env` dosyası asla versiyon kontrolüne eklenmemeli.
>
> `EMBEDDING_BACKEND`, `GENERATION_BACKEND` ve `VECTORDB_BACKEND` alanları enum ile doğrulanır — desteklenmeyen bir değer yazılırsa uygulama başlarken net bir hata verir (bkz. [Enum Yapısı](#-enum-yapısı)).
>
> ⚠️ **Resend sandbox kısıtlaması:** Domain doğrulanana kadar Resend hesabı yalnızca hesabı açan kişinin kendi e-posta adresine gönderim yapabilir (`onboarding@resend.dev` gönderen adresiyle). Gerçek kullanıcılara e-posta gönderebilmek için [resend.com/domains](https://resend.com/domains) üzerinden bir domain eklenip DNS kayıtları (SPF/DKIM) doğrulanmalı, ardından `EMAIL_FROM` o domain'e çevrilmelidir (örn. `noreply@hocayasor.com`). Bu adım tamamlanmadan mobil/web uygulaması gerçek kullanıcılara açılmamalıdır.

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

| Dosya | Format | Kayıt | Kaynak |
|---|---|---|---|
| `fetvalar.json` | JSONL (satır başı JSON) | 1362 | Diyanet |
| `pdf_fetvalar.json` | JSON array | 1031 | Diyanet |
| `islamweb_fetvalar.json` | JSON array | 95 | islamweb.net |

> ⚠️ `islamweb_fetvalar.json`, ham veriden **doğrudan** kullanılmaz. islamweb.net verisindeki `id` alanları ya eksik ya da geçerli bir UUID formatında değildir (`"islamweb-1360"`, `"58889"` gibi). Yüklemeden önce normalize script'i ile geçirilmesi gerekir:
>
> ```bash
> python normalize_islamweb.py assets/fatwas/islam_web.json assets/fatwas/islamweb_fetvalar.json
> ```
>
> Bu script, eksik/geçersiz id'ler için `source_url + question` alanlarından **deterministik** bir UUID5 üretir (rastgele değil) — böylece script tekrar çalıştırıldığında aynı id'ler üretilir ve `load_fatwas.py`'deki upsert (idempotent) mantığı bozulmaz. Çıktı raporunda "Çakışma" veya "Hata" satırı çıkarsa, ilgili kayıtları elle incelemek gerekir.

```bash
# 1. islamweb kaynağını normalize et (yalnızca yeni/güncellenen ham veri eklendiğinde gerekli)
python normalize_islamweb.py assets/fatwas/islam_web.json assets/fatwas/islamweb_fetvalar.json

# 2. Yükleme (idempotent — tekrar çalıştırılabilir)
python load_fatwas.py

# 3. Embedding doldurma (kaldığı yerden devam eder)
python fill_embeddings.py
```

---

## 📡 API Kullanımı

### `POST /api/v1/auth/register`

Yeni kullanıcı kaydı oluşturur (`is_verified=False`), Resend üzerinden e-posta adresine 6 haneli bir doğrulama kodu gönderir ve bir access token ile refresh token döner. Rate limit: **5/dakika**.

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "en_az_8_karakter"}'
```

> ℹ️ Hesap doğrulanana kadar `/auth/login` başarısız olur (`403 EMAIL_NOT_VERIFIED`). Gelen kutusunu (spam klasörü dahil) kontrol edip kodu `/auth/verify-email`'e gönder.

---

### `POST /api/v1/auth/verify-email`

E-posta ve 6 haneli kod ile hesabı doğrular. Kod, gönderildikten sonra `EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES` (varsayılan 15 dakika) süresince geçerlidir. Rate limit: **10/dakika**.

```bash
curl -X POST http://localhost:8000/api/v1/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "code": "325001"}'
```

**Yanıt (`200`):**

```json
{ "message": "E-posta adresiniz doğrulandı. Artık giriş yapabilirsiniz." }
```

**Hata Yanıtları:**

| Kod | Açıklama (mesaj) |
|---|---|
| `400` | Kod geçersiz veya süresi dolmuş (`INVALID_VERIFICATION_TOKEN`) |
| `429` | Çok fazla hatalı deneme yapıldı (`TOO_MANY_VERIFICATION_ATTEMPTS`) — yeni kod istenmeli |

---

### `POST /api/v1/auth/resend-verification`

Doğrulama kodu süresi dolmuş veya e-posta hiç ulaşmamışsa yeni bir kod gönderir. Rate limit: **3/dakika** (kötüye kullanımı önlemek için düşük tutulmuştur).

```bash
curl -X POST http://localhost:8000/api/v1/auth/resend-verification \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

---

### `POST /api/v1/auth/login`

E-posta ve şifre ile giriş yapar; hesap doğrulanmışsa bir access token ve bir refresh token döner. Rate limit: **5/dakika** (brute-force'a karşı).

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "en_az_8_karakter"}'
```

**Yanıt (`200`):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "rl4J3nB0hHF3X-DRPxcqMomk6Rcdg8pAKJtIOlUOHYET2SX0r3xL7OsZyx_tJoFD",
  "token_type": "bearer"
}
```

**Hata Yanıtları:**

| Kod | Açıklama (mesaj) |
|---|---|
| `401` | E-posta veya şifre hatalı (`INVALID_CREDENTIALS`) |
| `403` | Hesap henüz doğrulanmamış (`EMAIL_NOT_VERIFIED`) |
| `429` | Rate limit aşıldı (dakikada 5 istek) |

Bundan sonraki tüm `/fatwa/*`, `/auth/me` ve `/conversations/*` isteklerinde `access_token`, `Authorization: Bearer <access_token>` header'ında gönderilmelidir. `refresh_token`'ı istemci tarafında (mobil/web) güvenli bir şekilde sakla — sunucu tarafında sadece hash'i tutulur, kaybedilirse geri getirilemez, kullanıcı tekrar login olmalıdır.

---

### `POST /api/v1/auth/refresh`

Geçerli bir refresh token karşılığında yeni bir access token üretir. Refresh token'ın kendisi değişmez (rotasyon yapılmaz). Rate limit: **20/dakika**.

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<REFRESH_TOKEN>"}'
```

**Yanıt (`200`):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Hata Yanıtları:**

| Kod | Açıklama |
|---|---|
| `401` | Refresh token geçersiz, süresi dolmuş veya iptal edilmiş |
| `429` | Rate limit aşıldı (dakikada 20 istek) |

---

### `POST /api/v1/auth/logout`

Verilen refresh token'ı iptal eder (`revoked_at` alanı doldurulur). Bundan sonra bu refresh token ile yeni access token alınamaz. Rate limit: **10/dakika**.

```bash
curl -i -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<REFRESH_TOKEN>"}'
```

**Yanıt:** `204 No Content`

> ℹ️ Access token stateless (JWT) olduğu için, logout sonrası mevcut access token doğal süresi (en fazla 30 dakika) dolana kadar teknik olarak geçerliliğini korur. Bu kabul edilebilir bir trade-off'tur çünkü pencere kısa tutulmuştur; tam anlık iptal isteniyorsa access token'lar için de bir blacklist mekanizması eklenmesi gerekir (şu an yok).

---

### `GET /api/v1/auth/me`

Giriş yapmış kullanıcının profil bilgisini döner. Access token ile korumalıdır.

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**Yanıt (`200`):**

```json
{
  "id": "89403a8e-eff9-4dda-a7e1-f0e3141b792a",
  "name": "Ahmet Yılmaz",
  "email": "test@example.com",
  "is_active": true,
  "is_verified": true
}
```

---

### `PATCH /api/v1/auth/me`

Giriş yapmış kullanıcının adını günceller. Access token ile korumalıdır. Rate limit: **3/dakika**.

```bash
curl -X PATCH http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Ahmet Yılmaz"}'
```

**Parametreler:**

| Alan | Tip | Açıklama |
|---|---|---|
| `name` | string | 2–100 karakter |

**Yanıt (`200`):** güncellenmiş `UserResponse` (yukarıdaki `GET /auth/me` yanıtıyla aynı şema)

---

### `POST /api/v1/fatwa/ask`

Kullanıcının sorusuna ilgili fetvalar bulunarak cevap üretilir. Access token ile korumalıdır. Rate limit: **10/dakika**.

**İstek:**

```bash
curl -X POST http://localhost:8000/api/v1/fatwa/ask \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"question": "Faiz haram mı?", "top_k": 5}'
```

**Parametreler:**

| Alan | Tip | Varsayılan | Açıklama |
|---|---|---|---|
| `question` | string | — | Soru metni (3–1000 karakter) |
| `top_k` | integer | 5 | Kaç fetva baz alınsın (1–10) |
| `conversation_id` | string (UUID) | *(yok)* | Verilirse soru bu sohbete eklenir; verilmezse otomatik yeni bir sohbet açılır ve `conversation_id` yanıtta döner |

**Başarılı Yanıt (`200`):**

```json
{
  "conversation_id": "51fc5138-9ab9-4cd3-9169-d5eaced359c9",
  "log_id": "1c5fed58-db33-4a39-a406-5cd0345bf841",
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

`log_id`, sorunun `question_logs` tablosundaki kaydını temsil eder ve feedback endpoint'inde kullanılır. `conversation_id`, sonraki sorularda aynı sohbete devam etmek için tekrar gönderilmelidir; gönderilmezse yeni bir sohbet açılır.

**Hata Yanıtları:**

| Kod | Açıklama (mesaj `ResponseSignal` enum'undan gelir) |
|---|---|
| `401` | Access token geçersiz/eksik/süresi dolmuş |
| `404` | Kapsam dışı soru — ilgili fetva bulunamadı (`FATWA_NOT_FOUND`), **ya da** verilen `conversation_id` bulunamadı/başka bir kullanıcıya ait (`CONVERSATION_NOT_FOUND`) |
| `429` | Rate limit aşıldı (dakikada 10 istek) |
| `503` | Embedding veya LLM servis hatası (mesaj generic'tir, detay sunucu logunda tutulur) |

> ℹ️ `FATWA_NOT_FOUND`, o konuda veritabanında yeterince benzer fetva bulunamadığı anlamına gelir — sistemin bilerek verdiği bir "elimde güvenilir kaynak yok" cevabıdır, hata değildir. `VECTOR_MAX_DISTANCE` eşiğini gevşeterek (`.env`) daha fazla soruya cevap üretilebilir, ancak bu, alakasız fetvaların bağlam olarak kullanılma riskini artırır.

---

### `POST /api/v1/fatwa/feedback/{log_id}`

Bir soru-cevap logu için like/dislike geri bildirimi kaydeder. Sadece kendi sorduğunuz sorulara feedback verebilirsiniz. Tekrar çağrılırsa mevcut feedback güncellenir (upsert). Rate limit: **30/dakika**.

```bash
curl -X POST http://localhost:8000/api/v1/fatwa/feedback/1c5fed58-db33-4a39-a406-5cd0345bf841 \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"feedback": "like"}'
```

**Yanıt (`200`):**

```json
{
  "question_log_id": "1c5fed58-db33-4a39-a406-5cd0345bf841",
  "feedback": "like"
}
```

**Hata Yanıtları:**

| Kod | Açıklama |
|---|---|
| `403` | Bu log başka bir kullanıcıya ait |
| `404` | Belirtilen `log_id` bulunamadı |
| `429` | Rate limit aşıldı (dakikada 30 istek) |

---

### `GET /api/v1/conversations`

Giriş yapmış kullanıcının tüm sohbetlerini (en son güncellenen en üstte) listeler. Access token ile korumalıdır.

```bash
curl http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**Yanıt (`200`):**

```json
[
  {
    "id": "51fc5138-9ab9-4cd3-9169-d5eaced359c9",
    "title": "Faiz haram mı?",
    "created_at": "2026-07-05T12:33:39Z",
    "updated_at": "2026-07-05T12:33:41Z"
  }
]
```

---

### `GET /api/v1/conversations/{conversation_id}/messages`

Belirli bir sohbetin tüm soru-cevap geçmişini (kaynaklar ve feedback durumu dahil) döner. Sadece sohbetin sahibi erişebilir.

```bash
curl http://localhost:8000/api/v1/conversations/51fc5138-9ab9-4cd3-9169-d5eaced359c9/messages \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**Hata Yanıtları:**

| Kod | Açıklama |
|---|---|
| `403` | Bu sohbet başka bir kullanıcıya ait (`CONVERSATION_FORBIDDEN`) |
| `404` | Belirtilen `conversation_id` bulunamadı (`CONVERSATION_NOT_FOUND`) |

---

## 🔐 Güvenlik

- **Kimlik doğrulama:** Tüm `/fatwa/*`, `/auth/me` ve `/conversations/*` endpoint'leri access token ile korunur (`Authorization: Bearer <access_token>`). Şifreler bcrypt ile hashlenir, hiçbir zaman düz metin tutulmaz.
- **E-posta doğrulama:** Kayıt sonrası hesap `is_verified=False` olarak oluşturulur; Resend üzerinden gönderilen 6 haneli kod ile doğrulanmadan `/auth/login` başarılı olmaz. Kod süreli (varsayılan 15 dakika) ve deneme sayısı sınırlıdır (`TOO_MANY_VERIFICATION_ATTEMPTS`), bu sayede kod brute-force'a karşı korunur.
- **Access + Refresh token ayrımı:** Access token kısa ömürlü (30 dk) bir JWT'dir, çalınsa bile risk penceresi küçüktür. Refresh token uzun ömürlüdür (30 gün) ama veritabanında ham hali değil, sha256 hash'i tutulur (şifre gibi) — DB sızsa bile refresh token'lar doğrudan kullanılamaz.
- **Token iptali:** `/auth/logout` ile bir refresh token kalıcı olarak iptal edilebilir (`revoked_at`). İptal edilen bir refresh token bir daha yeni access token üretemez.
- **Rate limiting:** `slowapi` ile IP bazlı istek limitleri uygulanır — `/auth/login` ve `/auth/register` 5/dakika (brute-force ve spam hesap önleme), `/auth/verify-email` 10/dakika, `/auth/resend-verification` 3/dakika (e-posta spam'ini önlemek için düşük tutulmuştur), `/auth/refresh` 20/dakika, `/auth/logout` 10/dakika, `PATCH /auth/me` 3/dakika, `/fatwa/ask` 10/dakika, `/fatwa/feedback` 30/dakika.
- **Sohbet yetki kontrolü:** `/fatwa/ask`'a bir `conversation_id` gönderildiğinde, o sohbetin gerçekten isteği yapan kullanıcıya ait olduğu doğrulanır; aksi halde `404 CONVERSATION_NOT_FOUND` döner (başka bir kullanıcının sohbet id'sinin var olup olmadığını da sızdırmamak için `403` yerine bilinçli olarak `404` kullanılmıştır). `/conversations/{id}/messages` için ise sahiplik ihlali `403 CONVERSATION_FORBIDDEN` ile ayrıca işaretlenir.
- **Hata mesajları:** Servis hatalarında (embedding, LLM, veritabanı) client'a yalnızca generic bir mesaj döner; gerçek hata detayı (stack trace, iç servis mesajı) yalnızca sunucu loglarına yazılır, dışarı sızmaz. Tüm hata/başarı mesajları `models/enums/ResponseEnums.py` içinde merkezi olarak tanımlıdır (bkz. [Enum Yapısı](#-enum-yapısı)).
- **Global exception handler:** Beklenmeyen tüm hatalar `main.py`'deki merkezi handler'dan geçer, tutarlı bir `500` yanıtı döner.
- **Yetki kontrolü:** Feedback endpoint'i, log'un sahibi olmayan bir kullanıcının geri bildirim vermesini `403` ile engeller.
- **`JWT_SECRET_KEY` doğrulaması:** Uygulama başlarken bu değerin en az 32 karakter olduğunu kontrol eder; kısa/zayıf bir secret ile uygulama başlamaz.
- **Bilinen açık nokta — email enumeration:** `/auth/register`, e-posta zaten kayıtlıysa `409` ile bunu açıkça belirtir. Bu, kayıtlı e-postaların tespit edilebilmesine (düşük şiddette) izin verir. Rate limiting bu saldırıyı yavaşlatır ama tamamen engellemez. Tam çözüm (her zaman aynı yanıtı dönüp e-posta doğrulama linkiyle ilerlemek) e-posta gönderim altyapısı gerektirdiği için önceden bilinçli olarak ertelenmişti; e-posta doğrulama akışının eklenmesiyle bu konu kısmen adreslenmiştir.
- **Resend sandbox kısıtlaması (üretim öncesi tamamlanmalı):** Domain doğrulanmadan Resend yalnızca hesap sahibinin kendi e-postasına gönderim yapar. Gerçek kullanıcılara açılmadan önce bir domain eklenip DNS (SPF/DKIM) kayıtları doğrulanmalı ve `EMAIL_FROM` o domain'e çevrilmelidir (bkz. [Yapılandırma](#️-yapılandırma)).

---

## 📁 Proje Yapısı

```
hocaya_sor/
├── docker/
│   ├── docker-compose.yml
│   └── env/
│       └── .env.postgres
└── src/
    ├── main.py                          # FastAPI uygulaması, rate limiter, global exception handler
    ├── load_fatwas.py                   # Veri yükleme scripti (3 kaynak: fetvalar, pdf_fetvalar, islamweb)
    ├── normalize_islamweb.py            # islamweb ham verisini geçerli UUID'li JSON'a normalize eder
    ├── fill_embeddings.py               # Embedding doldurma scripti
    ├── test_rag.py                      # Terminal test scripti
    ├── assets/
    │   └── fatwas/                      # Ham JSON dosyaları (+ islam_web.json ham, islamweb_fetvalar.json normalize edilmiş)
    ├── controllers/
    │   ├── fatwa_controller.py          # Fetva sorma, sohbet oluşturma/bulma, loglama, feedback iş mantığı
    │   ├── auth_controller.py           # Kayıt/giriş/refresh/logout/e-posta doğrulama/profil iş mantığı
    │   └── conversation_controller.py   # Sohbet listeleme, mesaj geçmişi iş mantığı
    ├── routes/
    │   ├── fatwa_routes.py              # /ask, /feedback endpoint'leri (rate limitli)
    │   ├── auth_routes.py               # /register, /verify-email, /resend-verification,
    │   │                                 # /login, /refresh, /logout, /me (GET+PATCH) (rate limitli)
    │   └── conversation_routes.py       # /conversations, /conversations/{id}/messages
    ├── models/
    │   ├── db_connection.py             # SQLAlchemy session
    │   ├── enums/                       # Merkezi enum tanımları (bkz. Enum Yapısı)
    │   │   ├── LLMEnums.py
    │   │   ├── VectorDBEnum.py
    │   │   ├── FeedbackEnum.py
    │   │   └── ResponseEnums.py
    │   ├── schemas/
    │   │   ├── fatwa_schemas.py         # Ask/Feedback Pydantic şemaları (conversation_id dahil)
    │   │   ├── auth_schemas.py          # Register/Login/Refresh/Logout/VerifyEmail/Profil şemaları
    │   │   └── conversation_schemas.py  # Conversation/mesaj listesi response şemaları
    │   └── db_schemes/hocaya_sor/
    │       ├── alembic/                 # Migration ortamı (env.py, versions/)
    │       └── schemes/
    │           ├── base.py
    │           ├── fatwa.py             # SQLAlchemy ORM modeli
    │           ├── user.py              # Kullanıcı modeli (is_verified, name alanları dahil)
    │           ├── question_log.py      # Soru/cevap log modeli (conversation_id dahil)
    │           ├── question_feedback.py # Like/dislike feedback modeli
    │           ├── refresh_token.py     # Refresh token modeli (hash'lenmiş, revoke destekli)
    │           └── conversation.py      # Sohbet modeli (başlık, kullanıcı, zaman damgaları)
    ├── stores/
    │   ├── llm/
    │   │   ├── LLMInterface.py          # Soyut LLM arayüzü
    │   │   ├── LLMProviderFactory.py    # Provider seçici (Google/Groq, enum tabanlı)
    │   │   └── providers/
    │   │       ├── GoogleProvider.py    # Gemini implementasyonu
    │   │       └── GroqProvider.py      # Groq implementasyonu
    │   └── vectordb/
    │       ├── VectorDBInterface.py     # Soyut VectorDB arayüzü
    │       ├── VectorDBProviderFactory.py
    │       └── providers/
    │           └── PGVectorProvider.py  # pgvector implementasyonu
    └── helpers/
        ├── config.py                    # Pydantic Settings (enum tabanlı, JWT secret validasyonu)
        ├── security.py                  # JWT, bcrypt, refresh token hashleme, get_current_user
        ├── email.py                     # Resend entegrasyonu, doğrulama kodu üretimi/gönderimi
        └── rate_limiter.py              # slowapi Limiter instance'ı
```

---

## 🧩 Enum Yapısı

Provider seçimleri, feedback tipi ve tüm API hata/başarı mesajları `models/enums/` altında merkezi olarak tanımlıdır. Amaç: aynı string'in birden fazla dosyada elle tekrar yazılmasını önlemek ve `.env`'deki geçersiz bir değeri uygulama **başlarken** (çalışma zamanında sessizce değil) yakalamak.

```
models/enums/
├── LLMEnums.py          # EmbeddingBackendEnum, GenerationBackendEnum
├── VectorDBEnum.py      # VectorDBBackendEnum
├── FeedbackEnum.py      # FeedbackTypeEnum (like/dislike)
└── ResponseEnums.py     # ResponseSignal — tüm API hata/başarı mesajları
```

- **`LLMEnums.py` / `VectorDBEnum.py`** — `helpers/config.py` içindeki `Settings` sınıfında alan tipi olarak kullanılır. `.env`'de `GENERATION_BACKEND=grok` gibi geçersiz/typo'lu bir değer yazılırsa, uygulama başlarken `ValidationError` ile durur.
- **`FeedbackEnum.py`** — hem `models/schemas/fatwa_schemas.py` (Pydantic request/response) hem de `question_feedback.py` (SQLAlchemy ORM modeli) bu tek tanımı kullanır, ikisi arasında değer tutarsızlığı riski ortadan kalkar.
- **`ResponseEnums.py`** — `fatwa_controller.py`, `auth_controller.py`, `conversation_controller.py` ve `helpers/security.py` içindeki tüm `HTTPException(detail=...)` mesajları buradan gelir (`ResponseSignal.X.value`). Yeni bir hata mesajı eklemek/değiştirmek istediğinde tek yapman gereken bu dosyayı güncellemek. E-posta doğrulama ve sohbet akışı için eklenen üyeler:
  - `EMAIL_NOT_VERIFIED` — hesap doğrulanmadan login denendiğinde (`403`)
  - `INVALID_VERIFICATION_TOKEN` — kod geçersiz veya süresi dolmuşsa (`400`)
  - `TOO_MANY_VERIFICATION_ATTEMPTS` — art arda çok fazla hatalı kod denemesinde (`429`)
  - `CONVERSATION_NOT_FOUND` — verilen `conversation_id` bulunamadığında/başka bir kullanıcıya ait olduğunda (`404`)
  - `CONVERSATION_FORBIDDEN` — bir sohbetin mesaj geçmişine sahibi olmayan biri erişmeye çalıştığında (`403`)

Yeni bir provider veya durum eklerken: ilgili enum dosyasına yeni bir üye ekle, ardından `LLMProviderFactory.py` / `VectorDBProviderFactory.py` içindeki `if backend == ...` bloklarına karşılığını ekle.

---

## 🔄 Provider Değiştirme

Sistem provider soyutlamasıyla tasarlanmıştır. Sağlayıcıyı değiştirmek için:

**Embedding değiştirme (Google → Ollama):**

```env
# src/.env
EMBEDDING_BACKEND=ollama
```

```python
# models/enums/LLMEnums.py içinde EmbeddingBackendEnum'a OLLAMA = "ollama" ekle
# stores/llm/providers/OllamaProvider.py oluştur, LLMInterface'i implemente et
# stores/llm/LLMProviderFactory.py içine EmbeddingBackendEnum.OLLAMA koşulu ekle
```

**Generation (cevap üretimi) değiştirme (Google → Groq):**

```env
# src/.env
GENERATION_BACKEND=groq
GROQ_API_KEY=your_groq_key
```

Groq etkinken model fallback zinciri otomatik devreye girer: `llama-3.3-70b-versatile` → `llama-3.1-8b-instant` → `gemma2-9b-it`.

**VectorDB değiştirme (pgvector → Qdrant):**

```env
# src/.env
VECTORDB_BACKEND=qdrant
```

```python
# models/enums/VectorDBEnum.py içinde VectorDBBackendEnum'a QDRANT = "qdrant" ekle
# stores/vectordb/providers/QdrantProvider.py oluştur, VectorDBInterface'i implemente et
# stores/vectordb/VectorDBProviderFactory.py içine VectorDBBackendEnum.QDRANT koşulu ekle
```

---

## 🧑‍💻 Geliştirme

### Yeni migration oluşturma

```bash
cd src
alembic -c alembic.ini revision --autogenerate -m "açıklama"
```

⚠️ Autogenerate her çalıştığında modelle ilgisiz bazı drift'ler (örn. eski bir unique constraint farkı — `users_email_key`) migration dosyasına eklenebilir. Oluşan dosyayı **her zaman gözden geçir**, alakasız `drop_constraint`/`create_unique_constraint` satırlarını temizle, sonra:

```bash
alembic -c alembic.ini upgrade head
```

Yeni bir model dosyası eklediğinde (`schemes/` altına), onu hem `alembic/env.py` içine import etmeyi hem de gerekiyorsa `schemes/__init__.py`'ye eklemeyi unutma — aksi halde autogenerate yeni tabloyu görmez. (Örnek: `conversation.py` eklendiğinde bu adım atlanırsa, `question_logs.conversation_id`'nin işaret ettiği tablo tanınmaz ve foreign key autogenerate'i hata verir.)

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

### Rate limit değerlerini ayarlama

Limitler ilgili route dosyalarında `@limiter.limit(...)` decorator'ı ile tanımlıdır (`routes/fatwa_routes.py`, `routes/auth_routes.py`). Değiştirmek için decorator'daki string'i güncelle (örn. `"10/minute"` → `"20/minute"`). `@limiter.limit` kullanan her fonksiyonda mutlaka bir `request: Request` parametresi de bulunmalıdır — decorator, isteği yapan IP'yi bu nesneden çıkarır.

### Access/refresh token ömürlerini ayarlama

```env
# src/.env
JWT_ACCESS_EXPIRE_MINUTES=30
JWT_REFRESH_EXPIRE_DAYS=30
```

### Doğrulama kodu süresini ayarlama

```env
# src/.env
EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES=15
```

### Yeni bir fetva kaynağı eklerken

1. Ham JSON'u `assets/fatwas/` altına koy.
2. Eğer kaynaktaki `id` alanları UUID formatında değilse veya eksikse, `normalize_islamweb.py`'yi örnek alarak benzer bir normalize scripti yaz — id'siz/geçersiz id'ler için **deterministik** (rastgele değil) bir UUID5 üret, `source_dataset` alanını ata.
3. `load_fatwas.py`'ye yeni bir `<KAYNAK>_PATH` sabiti ve `load_<kaynak>_json()` fonksiyonu ekle, `main()` içindeki yükleme bloklarına dahil et.
4. `python load_fatwas.py` çalıştır, `Eklenen` sayısının beklediğin kayıt sayısına eşit olduğunu doğrula.
5. `python fill_embeddings.py` çalıştır, `Embedding bekleyen kayıt sayısı`nın yeni eklenen kayıt sayısına yakın olduğunu kontrol et.
6. `python test_rag.py` içindeki `test_sorular` listesine yeni kaynağa özgü 1-2 soru ekleyip `Kaynak:` alanında yeni `source_dataset` adının döndüğünü doğrula.

### Yeni bir hata mesajı ekleme

`models/enums/ResponseEnums.py` içindeki `ResponseSignal` enum'una yeni bir üye ekle, ardından ilgili controller'da `detail=ResponseSignal.YENI_MESAJ.value` şeklinde kullan. String'i asla doğrudan controller içine yazma — tek kaynaktan yönetim bozulur.

---

## 📜 Lisans

Apache-2.0 license