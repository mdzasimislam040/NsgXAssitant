import asyncio
from pyrogram.errors import (
    UserNotParticipant,
    UserAlreadyParticipant,
    FloodWait,
    ChatAdminRequired,
    RPCError,
)

import config
from clients import bot, assistant, LOGGER


async def _resolve_assistant_peer(chat_id: int):
    try:
        await assistant.get_chat(chat_id)
    except Exception as e:
        LOGGER.warning(f"Assistant get_chat error: {e}")


async def is_assistant_in_chat(chat_id: int) -> bool:
    try:
        await assistant.get_chat_member(chat_id, "me")
        return True
    except UserNotParticipant:
        return False
    except Exception:
        await _resolve_assistant_peer(chat_id)
        try:
            await assistant.get_chat_member(chat_id, "me")
            return True
        except Exception:
            return False


async def ensure_assistant_in_chat(chat_id: int):
    """
    Assistant chat mein hai ya nahi verify karta hai,
    aur agar nahi hai to auto-join ya link ke through enter karwata hai.
    """
    if await is_assistant_in_chat(chat_id):
        return True, ""

    try:
        chat = await bot.get_chat(chat_id)
    except Exception as e:
        LOGGER.warning(f"get_chat fail: {e}")
        chat = None

    # Public Group
    if chat and chat.username:
        try:
            await assistant.join_chat(chat.username)
            LOGGER.info(f"Assistant joined @{chat.username}")
            return True, ""
        except UserAlreadyParticipant:
            return True, ""
        except FloodWait:
            return False, "flood_wait"
        except RPCError as e:
            LOGGER.warning(f"Assistant username join error: {e}")

    # Private Group Invite Link
    try:
        link = getattr(chat, "invite_link", None) if chat else None
        if not link:
            link = await bot.export_chat_invite_link(chat_id)
        if link:
            try:
                await assistant.join_chat(link)
                LOGGER.info(f"Assistant joined private group {chat_id}")
                return True, ""
            except UserAlreadyParticipant:
                return True, ""
    except ChatAdminRequired:
        LOGGER.warning("Bot is not admin with invite link rights.")
    except FloodWait:
        return False, "flood_wait"
    except Exception as e:
        LOGGER.warning(f"Assistant invite link join error: {e}")

    # Bot adds assistant directly
    try:
        me_assistant = await assistant.get_me()
        await bot.add_chat_members(chat_id, me_assistant.id)
        await asyncio.sleep(1)
        if await is_assistant_in_chat(chat_id):
            return True, ""
    except Exception as e:
        LOGGER.warning(f"Bot add member error: {e}")

    return False, "manual_needed"