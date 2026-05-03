# -*- coding: utf-8 -*-
"""
Zenith Bot — Web Server (FastAPI)
Endpoint:
- GET  /auth/google/callback  — Google OAuth callback
- POST /payment/webhook       — Midtrans payment notification
- GET  /health                — Health check
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from loguru import logger

from app.config import settings
from app.services.auth_service import (
    exchange_google_code, get_user_by_telegram_id, create_user,
    create_jwt_token, save_session
)
from app.services.payment_service import handle_payment_notification

app = FastAPI(title="Zenith Bot API", version="1.0.0")

# Bot instance akan di-inject dari main.py
_bot = None


def set_bot(bot):
    global _bot
    _bot = bot


# =====================================================
# HEALTH CHECK
# =====================================================

@app.get("/health")
async def health():
    return {"status": "ok", "service": "Zenith Bot"}


# =====================================================
# GOOGLE OAUTH CALLBACK
# =====================================================

@app.get("/auth/google/callback")
async def google_callback(code: str = None, state: str = None, error: str = None):
    if error:
        logger.warning(f"Google OAuth error: {error}")
        return HTMLResponse(content=_html_page("Login Gagal", f"Error: {error}", success=False))

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    try:
        # Parse state: "telegram_id:nonce"
        parts = state.split(":")
        if len(parts) < 2:
            raise HTTPException(status_code=400, detail="Invalid state")
        telegram_id = int(parts[0])

        # Exchange code untuk user info Google
        userinfo = await exchange_google_code(code)
        if not userinfo or not userinfo.get("email"):
            return HTMLResponse(content=_html_page("Login Gagal", "Tidak bisa mendapatkan info dari Google.", success=False))

        email = userinfo["email"]
        google_id = userinfo.get("id") or userinfo.get("sub")
        name = userinfo.get("name") or email.split("@")[0]

        # Cek user existing
        user = await get_user_by_telegram_id(telegram_id)

        if not user:
            # Buat user baru
            user = await create_user(
                telegram_id=telegram_id,
                email=email,
                google_id=google_id,
                username=name,
            )

        if not user:
            return HTMLResponse(content=_html_page("Login Gagal", "Gagal membuat akun.", success=False))

        # Buat JWT dan simpan session
        token = create_jwt_token(user["id"], telegram_id)
        await save_session(user["id"], token, telegram_id)

        # Notif ke Telegram user
        if _bot:
            try:
                from app.services.subscription_service import get_active_subscription
                sub = await get_active_subscription(user["id"])
                tier = sub["tier"] if sub else None

                await _bot.send_message(
                    telegram_id,
                    f"Login Google berhasil!\n\nAkun: {email}\n\n"
                    "Ketik /start untuk membuka menu."
                )
            except Exception as e:
                logger.warning(f"Notif Telegram gagal: {e}")

        return HTMLResponse(content=_html_page(
            "Login Berhasil",
            f"Akun {email} berhasil terhubung ke Telegram kamu.\nKembali ke bot dan ketik /start.",
            success=True
        ))

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid telegram_id in state")
    except Exception as e:
        logger.error(f"Google callback error: {e}")
        return HTMLResponse(content=_html_page("Error", "Terjadi kesalahan sistem.", success=False))


# =====================================================
# MIDTRANS WEBHOOK
# =====================================================

@app.post("/payment/webhook")
async def payment_webhook(request: Request):
    try:
        body = await request.json()
        logger.info(f"Midtrans webhook received: {body.get('order_id')}")

        is_paid = await handle_payment_notification(body)

        if is_paid and _bot:
            order_id = body.get("order_id", "")
            # Ambil telegram_id dari order_id format: ZENITH-{tg_id}-{uuid}
            try:
                parts = order_id.split("-")
                if len(parts) >= 2:
                    telegram_id = int(parts[1])
                    from app.database import get_supabase
                    sb = get_supabase()
                    payment = sb.table("payments").select("tier, user_id").eq("midtrans_order_id", order_id).execute()
                    if payment.data:
                        tier = payment.data[0]["tier"]
                        await _bot.send_message(
                            telegram_id,
                            f"Pembayaran berhasil dikonfirmasi!\n\n"
                            f"Paket {tier.capitalize()} aktif selama 30 hari.\n"
                            "Ketik /start untuk membuka menu."
                        )
            except Exception as e:
                logger.warning(f"Notif pembayaran ke Telegram gagal: {e}")

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Payment webhook error: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/payment/finish")
async def payment_finish():
    return HTMLResponse(content=_html_page(
        "Pembayaran Selesai",
        "Terima kasih! Pembayaranmu sedang diproses.\nKembali ke Telegram dan ketik /start.",
        success=True
    ))


# =====================================================
# HTML HELPER
# =====================================================

def _html_page(title: str, message: str, success: bool = True) -> str:
    color = "#27ae60" if success else "#e74c3c"
    icon = "&#10003;" if success else "&#10007;"
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Zenith — {title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         display: flex; justify-content: center; align-items: center;
         min-height: 100vh; margin: 0; background: #0f0f0f; color: #fff; }}
  .card {{ background: #1a1a1a; border-radius: 12px; padding: 40px;
           max-width: 420px; text-align: center; border: 1px solid #333; }}
  .icon {{ font-size: 48px; color: {color}; margin-bottom: 16px; }}
  h1 {{ font-size: 22px; margin: 0 0 12px; }}
  p {{ color: #aaa; line-height: 1.6; white-space: pre-line; }}
  .brand {{ font-size: 13px; color: #555; margin-top: 24px; }}
</style>
</head>
<body>
<div class="card">
  <div class="icon">{icon}</div>
  <h1>{title}</h1>
  <p>{message}</p>
  <div class="brand">Zenith — Platform Analisa Saham IDX</div>
</div>
</body>
</html>"""
