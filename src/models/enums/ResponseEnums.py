from enum import Enum


class ResponseSignal(str, Enum):
    # Genel
    SERVER_ERROR = "Sunucu hatası oluştu. Lütfen daha sonra tekrar deneyin."

    # Fetva / RAG
    EMBEDDING_SERVICE_ERROR = "Şu anda soru işlenemiyor, lütfen birkaç dakika sonra tekrar deneyin."
    VECTORDB_SERVICE_ERROR = "Şu anda soru işlenemiyor, lütfen birkaç dakika sonra tekrar deneyin."
    GENERATION_SERVICE_ERROR = "Şu anda cevap üretilemiyor, lütfen birkaç dakika sonra tekrar deneyin."
    FATWA_NOT_FOUND = "İlgili fetva bulunamadı."

    # Soru logu / feedback
    QUESTION_LOG_NOT_FOUND = "Soru kaydı bulunamadı."
    FEEDBACK_FORBIDDEN = "Bu soruya geri bildirim verme yetkiniz yok."

    # Auth - kayıt / giriş
    EMAIL_ALREADY_REGISTERED = "Bu e-posta ile zaten bir hesap var."
    INVALID_CREDENTIALS = "E-posta veya şifre hatalı."
    ACCOUNT_DISABLED = "Hesap devre dışı bırakılmış."

    # Auth - token
    TOKEN_EXPIRED = "Token süresi dolmuş, tekrar giriş yapın."
    INVALID_TOKEN = "Geçersiz token."
    INVALID_TOKEN_TYPE = "Geçersiz token türü."
    USER_NOT_FOUND = "Kullanıcı bulunamadı."
    INVALID_REFRESH_TOKEN = "Geçersiz veya süresi dolmuş refresh token."