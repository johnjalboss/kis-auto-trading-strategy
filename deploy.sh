#!/bin/bash
# ============================================
# KIS Auto-Trading Bot - Oracle Cloud Deploy
# ============================================
# Usage: scp -r . opc@<oracle-ip>:~/kis-auto-trading/
#        ssh opc@<oracle-ip> 'bash ~/kis-auto-trading/deploy.sh'

set -e

DEPLOY_DIR="/home/ubuntu/kis-auto-trading"
SERVICE_NAME="kis-trading"

echo "=========================================="
echo "  KIS Auto-Trading Bot Deploy Script"
echo "=========================================="

# 1. System packages
echo "[1/6] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y python3-venv python3-pip 2>/dev/null || true

# 2. Virtual environment
echo "[2/6] Setting up Python virtual environment..."
cd "$DEPLOY_DIR"
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
echo "[3/6] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Check .env
echo "[4/6] Checking configuration..."
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Copy .env.example to .env and fill in your KIS API credentials."
    exit 1
fi

# Verify critical keys exist
if ! grep -q "KIS_APP_KEY=" .env || ! grep -q "KIS_CANO=" .env; then
    echo "ERROR: KIS_APP_KEY or KIS_CANO not set in .env"
    exit 1
fi
echo "  -> .env OK"

# 5. Install systemd service
echo "[5/6] Installing systemd service..."
sudo cp "$DEPLOY_DIR/kis-trading.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

# 6. Start service
echo "[6/6] Starting trading bot..."
sudo systemctl restart "$SERVICE_NAME"
sleep 3

# Check status
if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    echo ""
    echo "=========================================="
    echo "  ✅ Bot deployed and running!"
    echo "=========================================="
    echo ""
    echo "Useful commands:"
    echo "  sudo systemctl status $SERVICE_NAME    # Check status"
    echo "  sudo journalctl -u $SERVICE_NAME -f    # Follow logs"
    echo "  tail -f $DEPLOY_DIR/remote_trading_bot.log  # App logs"
    echo "  sudo systemctl stop $SERVICE_NAME      # Stop bot"
    echo "  sudo systemctl restart $SERVICE_NAME   # Restart bot"
else
    echo ""
    echo "❌ Bot failed to start. Check logs:"
    echo "  sudo journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi
