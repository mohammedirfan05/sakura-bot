"""
🌸 Sakura Bot — keep_alive.py
Lightweight HTTP server to keep the bot alive on free hosts like Render / Koyeb with ping services (e.g., UptimeRobot).
"""

import os
from aiohttp import web

async def handle(request):
    return web.Response(text="🌸 Sakura Bot is online and operational!")

async def start_keep_alive():
    port = int(os.getenv("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", handle)
    app.router.add_get("/health", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Keep-alive server started on port {port}")
