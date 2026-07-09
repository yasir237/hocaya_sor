"""
Resend üzerinden transactional e-posta gönderimi.
"""
import logging
import resend

from helpers.config import get_settings

settings = get_settings()
resend.api_key = settings.RESEND_API_KEY

logger = logging.getLogger(__name__)


def send_verification_email(to_email: str, code: str) -> None:
    # TEST MODU: Resend sandbox kısıtlaması nedeniyle (domain doğrulanmadan
    # yalnızca hesap sahibinin kendi adresine mail gidebiliyor) gerçek alıcı
    # yerine sabit test adresine (EMAIL_DEBUG_RECIPIENT) gönderiyoruz; kimin
    # için olduğunu anlaman için asıl alıcıyı konuya/gövdeye ekliyoruz.
    # Domain doğrulanınca EMAIL_DEBUG_MODE=False yapıp bu bloğu devre dışı bırak.
    actual_recipient = to_email
    subject = "Hocaya Sor — Doğrulama Kodunuz"
    recipient_note = ""

    if settings.EMAIL_DEBUG_MODE:
        actual_recipient = settings.EMAIL_DEBUG_RECIPIENT
        subject = f"[TEST → {to_email}] {subject}"
        recipient_note = f"""
                    <p style="color:#b45309;font-size:13px;background:#fffbeb;
                              padding:8px 12px;border-radius:6px;">
                        ⚠️ Test modu — bu kod aslında <b>{to_email}</b> için üretildi.
                        Kodu o kullanıcıya manuel ilet.
                    </p>
        """

    try:
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [actual_recipient],
            "subject": subject,
            "html": f"""
                <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
                    <h2>Hocaya Sor'a Hoş Geldiniz</h2>
                    {recipient_note}
                    <p>Hesabınızı aktifleştirmek için uygulamaya aşağıdaki kodu girin:</p>
                    <p style="font-size:32px;font-weight:bold;letter-spacing:8px;
                              background:#f3f4f6;padding:16px 24px;border-radius:8px;
                              text-align:center;color:#0f766e;">
                        {code}
                    </p>
                    <p style="color:#666;font-size:12px;">
                        Bu kod {settings.EMAIL_VERIFICATION_EXPIRE_MINUTES} dakika geçerlidir.
                        Bu isteği siz yapmadıysanız bu e-postayı görmezden gelebilirsiniz.
                    </p>
                </div>
            """,
        })
    except Exception:
        logger.exception("Doğrulama e-postası gönderilemedi (to=%s, gerçek_hedef=%s)", actual_recipient, to_email)
        # Kayıt akışını bozmamak için hatayı burada yutuyoruz (sadece logluyoruz).
        # Kullanıcı /auth/resend-verification ile tekrar deneyebilir.