#!/bin/bash
# =============================================================
# Zenith Bot — Deploy Script untuk VPS Ubuntu
# Jalankan sekali untuk setup awal:
#   chmod +x deploy.sh && ./deploy.sh
# =============================================================

set -e

BOT_DIR="/home/ubuntu/zenith_bot"
SERVICE_NAME="zenith-bot"
PYTHON="python3.11"

echo "=============================="
echo " Zenith Bot — Deploy Script"
echo "=============================="

# 1. Update sistem
echo "[1/8] Update sistem..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3.11 python3.11-venv python3-pip postgresql postgresql-contrib git

# 2. Setup direktori
echo "[2/8] Setup direktori..."
mkdir -p "$BOT_DIR"
mkdir -p "$BOT_DIR/logs"
mkdir -p "$BOT_DIR/charts"
cd "$BOT_DIR"

# 3. Setup venv
echo "[3/8] Setup virtual environment..."
if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip -q

# 4. Install dependencies
echo "[4/8] Install dependencies..."
pip install -r requirements.txt -q

# 5. Setup PostgreSQL lokal (cache VPS)
echo "[5/8] Setup PostgreSQL..."
sudo -u postgres psql -c "CREATE USER zenith_user WITH PASSWORD 'zenith_secure_pass_2024';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE zenith_cache OWNER zenith_user;" 2>/dev/null || true
sudo -u postgres psql -d zenith_cache -U zenith_user -f migrations/vps_schema.sql 2>/dev/null || true
echo "PostgreSQL setup selesai."

# 6. Copy .env jika belum ada
echo "[6/8] Cek environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "PENTING: File .env belum dikonfigurasi!"
    echo "Edit /home/ubuntu/zenith_bot/.env dengan API keys yang benar."
    echo "Setelah itu jalankan: sudo systemctl restart $SERVICE_NAME"
    echo ""
fi

# 7. Setup systemd service
echo "[7/8] Setup systemd service..."
sudo cp zenith-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

# 8. Start service (hanya jika .env sudah dikonfigurasi)
echo "[8/8] Start service..."
if grep -q "your_bot_token_here" .env; then
    echo ""
    echo "WARNING: .env belum dikonfigurasi. Service tidak distart."
    echo "Edit .env, lalu jalankan: sudo systemctl start $SERVICE_NAME"
else
    sudo systemctl start $SERVICE_NAME || true
    echo "Service started."
fi

echo ""
echo "=============================="
echo " Deploy selesai!"
echo "=============================="
echo ""
echo "Perintah berguna:"
echo "  sudo systemctl status $SERVICE_NAME   — cek status"
echo "  sudo systemctl restart $SERVICE_NAME  — restart bot"
echo "  sudo journalctl -u $SERVICE_NAME -f   — lihat log live"
echo "  sudo journalctl -u $SERVICE_NAME -n 50 — lihat 50 log terakhir"
echo ""
