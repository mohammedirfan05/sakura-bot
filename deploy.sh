#!/bin/bash
# 🌸 Sakura Bot — Oracle Cloud Fast Automated Deploy Script
set -e

echo "🚀 Starting Sakura Bot setup..."

# 1. Update system packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git curl nano

# 2. Set up project directory
PROJECT_DIR="/home/ubuntu/sakura-bot"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "📁 Creating bot directory at $PROJECT_DIR..."
    mkdir -p "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# 3. Setup Python Virtual Environment
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "📦 Installing/Updating Python dependencies..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 4. Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️ WARNING: .env file not found in $PROJECT_DIR!"
    echo "Please create a .env file with your BOT_TOKEN before starting the service."
fi

# 5. Create Systemd 24/7 Auto-restart Service
echo "⚙️ Configuring systemd service (sakura-bot)..."

sudo bash -c "cat << 'EOF' > /etc/systemd/system/sakura-bot.service
[Unit]
Description=Sakura Discord Bot 24/7 Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/sakura-bot
ExecStart=/home/ubuntu/sakura-bot/venv/bin/python main.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF"

# 6. Enable and reload systemd
sudo systemctl daemon-reload
sudo systemctl enable sakura-bot

echo ""
echo "✅ Sakura Bot installation completed!"
echo "------------------------------------------------------"
echo "📌 NEXT STEPS:"
echo "1. Put your .env file into /home/ubuntu/sakura-bot/.env"
echo "2. Start the bot with:   sudo systemctl start sakura-bot"
echo "3. Check bot status with: sudo systemctl status sakura-bot"
echo "4. View live logs with:   sudo journalctl -u sakura-bot -f"
echo "------------------------------------------------------"
