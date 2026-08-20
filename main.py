import os
import sys
import asyncio
from pathlib import Path

# ── Bulletproof Path Resolution & Auto-Unpack for KataBump / Pterodactyl ───
import zipfile

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


def setup_environment() -> Path:
    # 1. Check if core exists directly in BASE_DIR
    if (BASE_DIR / "core").exists():
        return BASE_DIR

    # 2. Check if core exists in any subdirectory (nested extraction)
    for path in BASE_DIR.glob("**/core"):
        if path.is_dir() and (path / "bot.py").exists():
            root_dir = path.parent
            sys.path.insert(0, str(root_dir))
            os.chdir(str(root_dir))
            print(f"📁 [Auto-Detect] Found bot files in: {root_dir.name}")
            return root_dir

    # 3. If core not found, check if an unextracted zip exists and unpack it
    zip_files = list(BASE_DIR.glob("*.zip"))
    for zf_path in zip_files:
        try:
            print(f"📦 [Auto-Extract] Found {zf_path.name}, extracting files...")
            with zipfile.ZipFile(zf_path, "r") as zip_ref:
                zip_ref.extractall(BASE_DIR)
            print(f"✅ [Auto-Extract] Extracted {zf_path.name} successfully.")
            if (BASE_DIR / "core").exists():
                return BASE_DIR
            for path in BASE_DIR.glob("**/core"):
                if path.is_dir() and (path / "bot.py").exists():
                    root_dir = path.parent
                    sys.path.insert(0, str(root_dir))
                    os.chdir(str(root_dir))
                    return root_dir
        except Exception as e:
            print(f"⚠️ Failed to auto-extract {zf_path.name}: {e}")

    # Debug: Print directory listing if core is still not found
    print("⚠️ 'core' directory was not found! Current directory contains:")
    for item in BASE_DIR.iterdir():
        print(f"  - {item.name} {'(folder)' if item.is_dir() else '(file)'}")
    return BASE_DIR


PROJECT_ROOT = setup_environment()
# ──────────────────────────────────────────────────────────────────────────

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()

from core.bot import SakuraBot
from utils.keep_alive import start_keep_alive

TOKEN = os.getenv("BOT_TOKEN")

INITIAL_EXTENSIONS = [
    "cogs.custom_commands",
    "cogs.fun",
    "cogs.logging",
    "cogs.moderation",
    "cogs.reaction_roles",
    "cogs.verification",
    "cogs.welcome",
]


async def main():
    if not TOKEN:
        print("❌ Error: BOT_TOKEN not found in .env file.")
        return

    # Start HTTP health check endpoint for cloud hosts (Render / Koyeb / UptimeRobot)
    try:
        await start_keep_alive()
    except Exception as e:
        print(f"⚠️ Could not start keep-alive HTTP server: {e}")

    async with SakuraBot() as bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())

