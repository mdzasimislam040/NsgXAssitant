import base64
import logging
import struct
import time
from pyrogram import Client
from pytgcalls import PyTgCalls
from motor.motor_asyncio import AsyncIOMotorClient

import config

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] - [%(levelname)s] - %(name)s - %(message)s",
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pytgcalls").setLevel(logging.WARNING)
LOGGER = logging.getLogger("MusicBot")


# ---------------------------------------------------------------------------
# Auto-Converter: Purono 267/263 Bytes Session String -> 271 Bytes Kurigram Format
# ---------------------------------------------------------------------------
def _fix_session_string(session_str: str, api_id: int) -> str:
    if not session_str:
        return ""
    session_str = session_str.strip()
    try:
        pad = len(session_str) % 4
        padded = session_str + ("=" * (4 - pad) if pad else "")
        raw = base64.urlsafe_b64decode(padded)

        # Jodi already 271 bytes hoy (v2 format)
        if len(raw) == 271:
            return session_str

        # 267 bytes: Pyrogram v1 64-bit format (>B?256sQ?)
        # byte 0: dc_id
        # byte 1..4: api_id (Kurigram e ekhane 4 byte api_id boshe)
        # byte 5: test_mode, auth_key, user_id, is_bot
        if len(raw) == 267:
            new_raw = raw[0:1] + struct.pack(">I", int(api_id)) + raw[1:]
            LOGGER.info("✅ Converted Pyrogram v1 session string (267B) to Kurigram format (271B)")
            return base64.urlsafe_b64encode(new_raw).decode().rstrip("=")

        # 263 bytes: Pyrogram v1 32-bit format (>B?256sI?)
        if len(raw) == 263:
            dc_id, test_mode, auth_key, user_id, is_bot = struct.unpack(">B?256sI?", raw)
            new_raw = struct.pack(">BI?256sQ?", dc_id, int(api_id), test_mode, auth_key, user_id, is_bot)
            LOGGER.info("✅ Converted Pyrogram v1 32-bit session string (263B) to Kurigram format (271B)")
            return base64.urlsafe_b64encode(new_raw).decode().rstrip("=")

    except Exception as e:
        LOGGER.warning(f"Session string converter notice: {e}")
    return session_str


# ---------------------------------------------------------------------------
# Compatibility shim: PyTgCalls 0.9.7 Supergroup ID fix (-100...)
# ---------------------------------------------------------------------------
try:
    from pyrogram.raw.types import UpdateGroupCall, PeerChat, PeerChannel

    if "chat_id" not in UpdateGroupCall.__dict__:
        def _shim_chat_id(self):
            peer = getattr(self, "peer", None)
            if isinstance(peer, PeerChat):
                return -peer.chat_id
            if isinstance(peer, PeerChannel):
                return -int(f"100{peer.channel_id}")
            return getattr(self, "_chat_id", None)

        UpdateGroupCall.chat_id = property(_shim_chat_id)
        LOGGER.info("✅ UpdateGroupCall.chat_id compatibility shim applied")
except Exception as _shim_err:
    LOGGER.warning(f"⚠️ UpdateGroupCall compatibility shim skip: {_shim_err}")

START_TIME = time.monotonic()

bot = Client(
    name="MusicBot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    in_memory=True,
)

# apnar dewa session string auto-convert hoye 271 bytes hoye jabe:
CLEAN_SESSION = _fix_session_string(config.STRING_SESSION, config.API_ID)

assistant = Client(
    name="Assistant",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=CLEAN_SESSION,
    in_memory=True,
)

call_py = PyTgCalls(assistant)

mongo_client = AsyncIOMotorClient(config.MONGO_DB_URI)
db = mongo_client["MusicBotDB"]