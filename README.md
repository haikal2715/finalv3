# Zenith Bot — Platform Analisa Saham IDX

Bot Telegram analisa saham IDX berbasis Hermes AI dengan sistem subscription.

## Stack Teknologi

| Komponen | Teknologi |
|---|---|
| Bot Framework | Aiogram 3.7 |
| AI Engine | Hermes (OpenRouter > Groq > Cerebras > Gemini > Cloudflare > LLM7 > SiliconFlow) |
| Database Permanen | Supabase (PostgreSQL) |
| Database Cache | PostgreSQL VPS (rolling 2 hari) |
| Data Market | tvdatafeed (TradingView) + yfinance |
| Payment | Midtrans Snap |
| Web Server | FastAPI + Uvicorn |
| Scheduler | APScheduler |
| Deploy | Ubuntu VPS + systemd |

## Struktur Proyek

```
zenith_bot/
├── main.py                      # Entry point
├── requirements.txt
├── .env.example
├── zenith-bot.service           # Systemd service
├── deploy.sh                    # Deploy script
├── migrations/
│   ├── supabase_schema.sql      # Schema Supabase (jalankan pertama)
│   ├── supabase_additional.sql  # Schema tambahan Supabase
│   └── vps_schema.sql           # Schema PostgreSQL VPS cache
└── app/
    ├── config.py                # Settings + pricing config
    ├── database.py              # Koneksi Supabase + VPS PostgreSQL
    ├── logger.py                # Loguru setup
    ├── scheduler.py             # APScheduler jobs
    ├── web_server.py            # FastAPI (OAuth + Midtrans webhook)
    ├── handlers/
    │   ├── start_handler.py     # /start, login, register
    │   ├── menu_handler.py      # Menu utama, profil, langganan
    │   ├── request_handler.py   # Request analisa
    │   ├── alert_handler.py     # Price alert
    │   ├── skill_handler.py     # Skill switch + upload
    │   └── admin_handler.py     # Semua command admin
    ├── services/
    │   ├── hermes_service.py    # Hermes AI + fallback chain
    │   ├── market_service.py    # Data OHLCV + indikator + chart
    │   ├── signal_service.py    # Signal pipeline + cache
    │   ├── news_service.py      # RSS + GNews
    │   ├── skill_service.py     # Manajemen skill
    │   ├── auth_service.py      # JWT + Google OAuth
    │   ├── subscription_service.py
    │   ├── usage_service.py     # Daily limits
    │   └── payment_service.py   # Midtrans
    ├── middlewares/
    │   └── auth_middleware.py   # Inject user data ke handler
    └── utils/
        ├── keyboards.py         # Semua inline keyboard
        ├── states.py            # FSM states
        └── helpers.py           # Utility functions
```

## Setup Awal

### 1. Clone & Konfigurasi

```bash
git clone <repo> zenith_bot
cd zenith_bot
cp .env.example .env
nano .env  # Isi semua API keys
```

### 2. Jalankan Migration Supabase

Buka Supabase SQL Editor, jalankan berurutan:
1. `migrations/supabase_schema.sql`
2. `migrations/supabase_additional.sql`

### 3. Deploy ke VPS

```bash
chmod +x deploy.sh
./deploy.sh
```

### 4. Cek Status

```bash
sudo systemctl status zenith-bot
sudo journalctl -u zenith-bot -f
```

## Environment Variables Wajib

Lihat `.env.example` untuk daftar lengkap. Yang paling kritis:

- `BOT_TOKEN` — dari @BotFather
- `ADMIN_TELEGRAM_ID` — Telegram ID kamu
- `SUPABASE_URL` + `SUPABASE_SERVICE_KEY`
- `OPENROUTER_API_KEY` (provider utama Hermes)
- `GROQ_API_KEY` (fallback cepat)
- `GEMINI_API_KEY` (fallback multimodal)
- `MIDTRANS_SERVER_KEY` + `MIDTRANS_CLIENT_KEY`
- `JWT_SECRET_KEY` — random string panjang

## Tier & Harga

| Tier | Harga | Request/hari | Alert/hari |
|---|---|---|---|
| Bronze | Rp 59.000 | 1x | 1x |
| Silver | Rp 109.000 | 3x | 2x |
| Diamond | Rp 189.000 | 6x | 3x |

## Jadwal Scheduler

| Job | Waktu | Fungsi |
|---|---|---|
| Pre-analisa malam | 20:00 WIB | Scan + cache 30 saham |
| Distribusi sinyal | 09:15 WIB (Sen-Jum) | Kirim sinyal ke subscriber |
| Alert checker | Tiap 5 menit (jam bursa) | Monitor price alert |
| Weekend learning | Jumat 15:30 WIB | Hermes review SL hit |
| Cleanup cache | Sabtu 00:00 WIB | Hapus cache expired |
| Expire subs | 00:05 WIB tiap hari | Update status expired |

## Admin Commands

- `/dashboard` — Panel admin utama
- `Hermes Admin` — Chat Hermes tanpa limit (3 mode)
- `Tambah Skill` — Upload skill global Hermes
- `Saran Analisa` — Input konteks market ke Hermes
- `Tambah User` — Manual onboarding influencer/mitra
- `Tambah Kutipan` — Tambah kutipan harian

## Notes Penting

1. **tvdatafeed** — Tidak perlu API key, tapi butuh koneksi ke TradingView. Test dulu di VPS dengan `python3 -c "from tvdatafeed import TvDatafeed; tv = TvDatafeed(); print(tv.get_hist('BBCA', 'IDX', n_bars=5))"`
2. **Google Service Account** — Jika perlu, simpan sebagai file `.json` terpisah, JANGAN di `.env`
3. **Supabase free tier** — 500MB DB cukup untuk 6-12 bulan pertama
4. **Midtrans sandbox** — Set `MIDTRANS_IS_PRODUCTION=false` untuk testing
