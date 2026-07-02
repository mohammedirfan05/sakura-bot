# 🖤 KARMA Bot

A fully custom, feature-rich Discord bot built for the **KARMA** community.

## Features

| Feature | Description |
|---|---|
| 👋 Welcome | Styled embed with avatar on member join |
| ⚔️ Moderation | /ban /kick /timeout /warn /warnings /unwarn /clear /lock /unlock |
| 📝 Logging | Message edits/deletes, voice, role changes |
| 📊 Leveling | XP per message, level-up, milestone roles |
| 🎭 Reaction Roles | Self-assignable platform & ping roles |
| 🎮 Fun | /8ball /coinflip /meme /cat /dog /avatar /banner |
| 📚 Utility | /rules /faq /help /socials /customs /ping |

---

## Setup

### 1. Create Your Bot
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application → Bot
3. Enable all **Privileged Gateway Intents**: `Presence`, `Server Members`, `Message Content`
4. Copy your **Bot Token**

### 2. Invite the Bot
Use this URL (replace `YOUR_CLIENT_ID`):
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your BOT_TOKEN
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run Locally (Testing)
```bash
python main.py
```

---

## 🚀 Free 24/7 Hosting — Oracle Cloud Always Free

Oracle Cloud offers a **forever free** ARM VM with up to 24GB RAM. This is the best free option for running a Discord bot 24/7 without it ever sleeping.

### Step-by-Step

1. **Sign up** at [cloud.oracle.com](https://cloud.oracle.com) (requires credit card for identity — you will NOT be charged).
2. **Create a VM Instance:**
   - Shape: `VM.Standard.A1.Flex` (ARM)
   - OCPUs: 1, RAM: 6 GB (stays in Always Free limits)
   - OS: Ubuntu 22.04
3. **SSH into your VM:**
   ```bash
   ssh ubuntu@YOUR_VM_IP
   ```
4. **Install Python & Git:**
   ```bash
   sudo apt update && sudo apt install python3.11 python3-pip git -y
   ```
5. **Clone your bot repo:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/karma-bot.git
   cd karma-bot
   pip3 install -r requirements.txt
   ```
6. **Create your .env file:**
   ```bash
   cp .env.example .env
   nano .env  # paste your bot token
   ```
7. **Install PM2 (process manager):**
   ```bash
   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
   sudo apt install nodejs -y
   sudo npm install pm2 -g
   ```
8. **Start the bot with PM2:**
   ```bash
   pm2 start main.py --interpreter python3 --name karma-bot
   pm2 save
   pm2 startup   # follow the outputted command to enable auto-restart on reboot
   ```
9. **Done!** Your bot runs 24/7 and automatically restarts if it crashes.

### PM2 Commands
| Command | Description |
|---|---|
| `pm2 status` | Check if bot is running |
| `pm2 logs karma-bot` | View live logs |
| `pm2 restart karma-bot` | Restart the bot |
| `pm2 stop karma-bot` | Stop the bot |

---

## Project Structure

```
karma-bot/
├── main.py                  # Bot entry point
├── requirements.txt
├── Procfile                 # Railway deployment
├── runtime.txt              # Python version
├── .env.example             # Template for secrets
├── core/
│   ├── bot.py               # Core bot class setup
│   ├── config.py            # All IDs, colours, constants
│   └── database.py          # SQLite async database handler
├── utils/
│   └── embeds.py            # Embed helpers
└── cogs/
    ├── welcome.py           # Join/leave messages
    ├── moderation.py        # All mod commands
    ├── logging.py           # Event logging
    ├── leveling.py          # XP & level system
    ├── fun.py               # Fun commands
    ├── reaction_roles.py    # Self-assignable roles
    └── custom_commands.py   # Utility commands
```

---

## Customising Reaction Roles

Open `cogs/reaction_roles.py` and add your Discord role IDs to the dictionaries at the top:

```python
PLATFORM_ROLES = {
    "💻 PC":          123456789012345678,  # Replace with actual role ID
    "🎮 PlayStation":  123456789012345679,
    ...
}
```

Then run `/setup-roles` in your Discord server to refresh the panel.

---

Built with ❤️ and 🖤 for the KARMA community.
