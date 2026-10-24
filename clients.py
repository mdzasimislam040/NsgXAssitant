import logging
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

# ---------------------------------------------------------------------------
# Compatibility shim: PyTgCalls 0.9.7 + Kurigram / Pyrogram
# Supergroup ID (-100...) thikvabe resolve korar jonno shim.
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
        logging.getLogger("MusicBot").info(
            "✅ UpdateGroupCall.chat_id compatibility shim applied (Supergroup fixed)"
        )
except Exception as _shim_err:
    logging.getLogger("MusicBot").warning(
        f"⚠️ UpdateGroupCall compatibility shim skip: {_shim_err}"
    )

LOGGER = logging.getLogger("MusicBot")

START_TIME = time.monotonic()

bot = Client(
    name="MusicBot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    in_memory=True,
)

assistant = Client(
    name="Assistant",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.STRING_SESSION,
    in_memory=True,
)

call_py = PyTgCalls(assistant)

mongo_client = AsyncIOMotorClient(config.MONGO_DB_URI)
db = mongo_client["MusicBotDB"]