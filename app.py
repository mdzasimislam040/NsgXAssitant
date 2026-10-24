import asyncio
import threading

import aiohttp
import uvicorn
from fastapi import FastAPI
from pyrogram import idle
from pyrogram.types import BotCommand

import config
import db
import botstate
from clients import bot, assistant, call_py, LOGGER
from helpers import CREDIT_LINE

import play  # noqa: F401

web = FastAPI()


@web.get("/")
async def root():
    return {"status": "running", "credit": "Power by Zasim Credit NSG CHEATS"}


def run_web():
    uvicorn.run(web, host="0.0.0.0", port=config.PORT, log_level="warning")


async def keep_alive():
    if not config.RENDER_EXTERNAL_URL:
        return
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(config.RENDER_EXTERNAL_URL, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    LOGGER.info(f"Keep-alive status: {resp.status}")
            except Exception as e:
                LOGGER.warning(f"Keep-alive ping failed: {e}")
            await asyncio.sleep(config.PING_INTERVAL)


async def register_bot_commands():
    try:
        await bot.set_bot_commands(
            [
                BotCommand("play", "Gaana bajao"),
                BotCommand("skip", "Agla gaana"),
                BotCommand("pause", "Pause karo"),
                BotCommand("resume", "Resume karo"),
                BotCommand("stop", "Band karo"),
                BotCommand("userbotjoin", "Assistant ko add karo"),
                BotCommand("reload", "Bot refresh karo"),
                BotCommand("id", "Chat & User ID dekho"),
            ]
        )
    except Exception as e:
        LOGGER.warning(f"Set bot commands error: {e}")


async def _run_once():
    # 1. Start Main Bot
    if not getattr(bot, "is_connected", False):
        await bot.start()
    LOGGER.info("✅ Bot client started")

    # 2. Start Assistant (Userbot)
    if not getattr(assistant, "is_connected", False):
        await assistant.start()
    LOGGER.info("✅ Assistant client started")

    # Fast caching of recent dialogs
    try:
        async for dialog in assistant.get_dialogs(limit=25):
            pass
        LOGGER.info("✅ Assistant dialogs cached")
    except Exception as e:
        LOGGER.warning(f"Assistant dialog cache error: {e}")

    # 3. Start PyTgCalls Engine
    await call_py.start()
    LOGGER.info("✅ PyTgCalls engine started")

    try:
        botstate.set_enabled(await db.get_bot_status())
    except Exception:
        botstate.set_enabled(True)

    await register_bot_commands()

    if config.LOG_GROUP_ID:
        try:
            await bot.send_message(
                config.LOG_GROUP_ID,
                f"✅ **Music Bot Started Successfully**\n\n{CREDIT_LINE}",
                disable_web_page_preview=True,
            )
        except Exception as e:
            LOGGER.warning(f"Log group notification error: {e}")

    keep_alive_task = asyncio.create_task(keep_alive())

    try:
        await idle()
    finally:
        keep_alive_task.cancel()
        try:
            await bot.stop()
        except Exception:
            pass
        try:
            await assistant.stop()
        except Exception:
            pass
        LOGGER.info("🛑 Bot stopped")


async def main():
    while True:
        try:
            await _run_once()
            break
        except Exception as e:
            LOGGER.error(f"Process crashed, restarting in 10s: {e}")
            await asyncio.sleep(10)


if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    asyncio.get_event_loop().run_until_complete(main())