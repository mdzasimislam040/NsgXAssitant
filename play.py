import random
import time
import asyncio

from pyrogram import filters, StopPropagation
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)
from pytgcalls.types.input_stream import AudioPiped
from pytgcalls.exceptions import NoActiveGroupCall

import config
import db
import music_queue as q
import progress
import botstate
from clients import bot, assistant, call_py, LOGGER
from youtube import search_track, get_stream_url
from helpers import (
    smallcaps_title,
    random_processing_text,
    fancy_italic,
    duration_to_seconds,
    expandable_quote,
    strip_quotes,
    DIVIDER,
    bullet_lines,
    CREDIT_LINE,
)

from nowplaying import generate_now_playing_card
from assistant_join import ensure_assistant_in_chat, ensure_assistant_started

OWNER_FILTER = filters.user(config.OWNER_ID) if config.OWNER_ID else filters.create(lambda _, __, ___: False)
ADMIN_STATUSES = (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)

_pending_addvd = set()
_pending_addvd2 = set()

_SEND_MEDIA_MAP_NAME = {"photo": "send_photo", "video": "send_video", "animation": "send_animation"}


def _btn(text: str, *, style: str = None, **kwargs) -> InlineKeyboardButton:
    if style:
        try:
            return InlineKeyboardButton(text, style=style, **kwargs)
        except TypeError:
            pass
    return InlineKeyboardButton(text, **kwargs)


def _controls_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                _btn("▶️", callback_data="m_resume", style="success"),
                _btn("⏸", callback_data="m_pause", style="primary"),
                _btn("🔁", callback_data="m_replay", style="primary"),
                _btn("⏭", callback_data="m_skip", style="primary"),
                _btn("⏹", callback_data="m_stop", style="danger"),
            ],
            [
                _btn(f"📢 {smallcaps_title('channel')}", url=config.CHANNEL_URL, style="primary"),
                _btn(f"🛠 {smallcaps_title('support')}", url=config.SUPPORT_URL, style="primary"),
            ],
            [_btn(f"⊙ {smallcaps_title('close')} ⊙", callback_data="m_close", style="danger")],
        ]
    )


def _start_keyboard(bot_username: str):
    return InlineKeyboardMarkup(
        [
            [
                _btn(
                    f"➕ {smallcaps_title('add me to your group')}",
                    url=f"https://t.me/{bot_username}?startgroup=true",
                    style="success",
                )
            ],
            [
                _btn(f"👑 {smallcaps_title('owner')}", url=config.OWNER_URL, style="primary"),
                _btn(f"🛠 {smallcaps_title('support')}", url=config.SUPPORT_URL, style="primary"),
            ],
            [
                _btn(f"📢 {smallcaps_title('channel')}", url=config.CHANNEL_URL, style="primary"),
                _btn(f"❓ {smallcaps_title('help')}", callback_data="help_menu", style="primary"),
            ],
        ]
    )


def _assistant_invite_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                _btn(
                    f"➕ {smallcaps_title('add assistant manually')}",
                    url=f"https://t.me/{config.ASSISTANT_USERNAME}?startgroup=true",
                    style="success",
                )
            ]
        ]
    )


async def _safe_quote_send(action, text: str):
    try:
        return await action(text)
    except Exception as e:
        LOGGER.warning(f"Quote send fallback: {e}")
        return await action(strip_quotes(text))


async def _send_welcome(chat_id: int, text: str, reply_markup, media: dict = None):
    if media:
        send_func = getattr(bot, _SEND_MEDIA_MAP_NAME.get(media["media_type"], "send_photo"))
        try:
            return await _safe_quote_send(
                lambda t: send_func(chat_id, media["file_id"], caption=t, reply_markup=reply_markup),
                text,
            )
        except Exception as e:
            LOGGER.warning(f"Media welcome fail: {e}")
    return await _safe_quote_send(
        lambda t: bot.send_message(chat_id, t, reply_markup=reply_markup, disable_web_page_preview=True),
        text,
    )


async def _edit_body(cq_message, text: str, reply_markup):
    if cq_message.photo or cq_message.video or cq_message.animation:
        await _safe_quote_send(lambda t: cq_message.edit_caption(t, reply_markup=reply_markup), text)
    else:
        await _safe_quote_send(
            lambda t: cq_message.edit_text(t, reply_markup=reply_markup, disable_web_page_preview=True),
            text,
        )


async def _is_group_admin(client, chat_id: int, user_id: int) -> bool:
    if config.OWNER_ID and user_id == config.OWNER_ID:
        return True
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in ADMIN_STATUSES
    except Exception:
        return False


async def _can_control(client, chat_id: int, user_id: int) -> bool:
    if await _is_group_admin(client, chat_id, user_id):
        return True
    track = q.get_now_playing(chat_id)
    return bool(track and track.get("requested_by_id") == user_id)


def _welcome_text(user_name: str, user_id: int, bot_name: str, bot_username: str) -> str:
    user_tag = f"[{smallcaps_title(user_name)}](tg://user?id={user_id})"
    bot_tag = f"[{fancy_italic(bot_name)}](https://t.me/{bot_username})"
    body = (
        f"🦋 ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ {bot_tag}\n"
        f"『 ᴘʀᴇᴍɪᴜᴍ ✧ ᴀᴅ-ꜰʀᴇᴇ ✧ ᴜʟᴛʀᴀ sᴍᴏᴏᴛʜ 』\n\n"
        f"🦋 ʜɪɢʜ • Qᴜᴀʟɪᴛʏ • ᴍᴜsɪᴄ • ʙᴏᴛ\n"
        f"ғᴏʀ ᴛᴇʟᴇɢʀᴀᴍ ɢʀᴏᴜᴘs & ᴄʜᴀɴɴᴇʟs\n\n"
        f"🦋✦ ɪɴsᴛᴀɴᴛ sᴛʀᴇᴀᴍɪɴɢ\n"
        f"🦋✦ ᴜʟᴛʀᴀ sᴍᴏᴏᴛʜ ᴘʟᴀʏʙᴀᴄᴋ\n"
        f"🦋✦ ᴄʀʏsᴛᴀʟ ᴄʟᴇᴀʀ sᴏᴜɴᴅ • ɴᴏ ʟᴀɢ\n\n"
        f"{CREDIT_LINE}\n\n"
        f"╭───────────── ✦ ─────────────╮\n"
        f"❖ ᴇɴᴊᴏʏ ᴛʜᴇ ᴍᴜsɪᴄ ❖\n"
        f"╰───────────── ✦ ─────────────╯"
    )
    return f"🦋 ʜᴇʏ {user_tag}..!! ✦\n\n" + expandable_quote(body)


def _group_start_text(bot_name: str) -> str:
    return f"✨ {fancy_italic(bot_name)} ɪs ᴏɴʟɪɴᴇ ᴀɴᴅ ʀᴇᴀᴅʏ ✨\n\n" + expandable_quote(
        "🎧 ᴍᴜsɪᴄ ᴘᴀɴᴇʟ\n"
        "╰┈➤ /play <sᴏɴɢ ɴᴀᴍᴇ> — ɢᴀᴀɴᴀ ʙᴀᴊᴀᴏ\n"
        "╰┈➤ /skip • /pause • /resume • /stop\n"
        "╰┈➤ /userbotjoin — ᴀssɪsᴛᴀɴᴛ ᴋᴏ ᴊᴏɪɴ ᴋᴀʀᴀᴏ\n\n"
        f"{CREDIT_LINE}\n\n"
        "•── ⋅ ⋅  ────── ⋅᯽⋅ ────── ⋅ ⋅ ⋅──•"
    )


HELP_TEXT = (
    "🦋 **ᴀᴠᴀɪʟᴀʙʟᴇ ᴄᴏᴍᴍᴀɴᴅs**\n\n"
    "`/play <song>` — gaana bajao ya queue mein daalo\n"
    "`/skip` — agla gaana _(admin only)_\n"
    "`/pause` — pause karo _(admin only)_\n"
    "`/resume` — resume karo _(admin only)_\n"
    "`/stop` — band karo _(admin only)_\n"
    "`/userbotjoin` — assistant ko group mein bulao\n"
    "`/reload` — bot refresh karo\n"
    "`/id` — apni/group ki ID dekho\n\n"
    f"{CREDIT_LINE}"
)


@bot.on_message(filters.command("on") & OWNER_FILTER)
async def on_command(client, message: Message):
    botstate.set_enabled(True)
    await db.set_bot_status(True)
    await message.reply_text(f"✅ {smallcaps_title('bot on kar diya gaya hai')}.")


@bot.on_message(filters.command("off") & OWNER_FILTER)
async def off_command(client, message: Message):
    botstate.set_enabled(False)
    await db.set_bot_status(False)
    await message.reply_text(f"🔴 {smallcaps_title('bot off kar diya gaya hai')}.")


def _off_blocker(_, __, message: Message) -> bool:
    if botstate.is_enabled():
        return False
    text = message.text or message.caption or ""
    return not text.startswith(("/on", "/off"))


@bot.on_message(filters.create(_off_blocker), group=-1)
async def _blocked_while_off(client, message: Message):
    raise StopPropagation


@bot.on_callback_query(filters.create(lambda _, __, cq: not botstate.is_enabled()), group=-1)
async def _blocked_cb_while_off(client, cq: CallbackQuery):
    await cq.answer(smallcaps_title("bot abhi off hai"), show_alert=True)
    raise StopPropagation


@bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await db.add_user(message.from_user.id)
    me = await bot.get_me()

    if message.chat.type != "private":
        await db.add_chat(message.chat.id)
        media = await db.get_group_start_media()
        await _send_welcome(
            message.chat.id,
            _group_start_text(me.first_name),
            _start_keyboard(me.username),
            media,
        )
    else:
        media = await db.get_start_media()
        await _send_welcome(
            message.chat.id,
            _welcome_text(message.from_user.first_name, message.from_user.id, me.first_name, me.username),
            _start_keyboard(me.username),
            media,
        )


@bot.on_callback_query(filters.regex("^help_menu$"))
async def help_menu_cb(client, cq: CallbackQuery):
    await cq.answer()
    await _edit_body(cq.message, HELP_TEXT, InlineKeyboardMarkup([[_btn(f"🔙 {smallcaps_title('back')}", callback_data="back_to_start", style="primary")]]))


@bot.on_callback_query(filters.regex("^back_to_start$"))
async def back_to_start_cb(client, cq: CallbackQuery):
    await cq.answer()
    me = await bot.get_me()
    text = _group_start_text(me.first_name) if cq.message.chat.type != "private" else _welcome_text(cq.from_user.first_name, cq.from_user.id, me.first_name, me.username)
    await _edit_body(cq.message, text, _start_keyboard(me.username))


@bot.on_message(filters.command(["userbotjoin", "assistantjoin"]) & filters.group)
async def manual_userbot_join(client, message: Message):
    chat_id = message.chat.id
    status = await message.reply_text(f"⏳ {smallcaps_title('assistant joining group')}...")
    joined, reason = await ensure_assistant_in_chat(chat_id)
    if joined:
        await status.edit_text(f"✅ {smallcaps_title('assistant joined successfully')}! Ab `/play` karo.")
    else:
        await status.edit_text(
            f"❌ **{smallcaps_title('assistant auto-join failed')}!**\n"
            f"👉 @{config.ASSISTANT_USERNAME} {smallcaps_title('ko manually group mein add karo aur admin banao')}.",
            reply_markup=_assistant_invite_keyboard(),
        )


@bot.on_message(filters.command(["play", "vplay"], prefixes=["/", "!", "."]) & filters.group)
async def play_command(client, message: Message):
    if len(message.command) < 2 and not message.reply_to_message:
        return await message.reply_text(
            f"❌ {smallcaps_title('gaane ka naam bhi likho')}!\nExample: `/play Aaj Ki Raat`"
        )

    status = await message.reply_text(random_processing_text())
    chat_id = message.chat.id

    try:
        await ensure_assistant_started()

        if len(message.command) >= 2:
            query = message.text.split(None, 1)[1]
        elif message.reply_to_message and message.reply_to_message.audio:
            query = message.reply_to_message.audio.title or "Audio Track"
        else:
            return await status.edit_text("❌ Song not detected.")

        requester = message.from_user.mention if message.from_user else "Someone"
        requester_id = message.from_user.id if message.from_user else None

        joined, reason = await ensure_assistant_in_chat(chat_id)
        if not joined:
            return await status.edit_text(
                f"❌ **{smallcaps_title('assistant account group mein nahi hai')}!**\n\n"
                f"👉 @{config.ASSISTANT_USERNAME} {smallcaps_title('ko group mein add karo aur admin rights do')}.\n"
                f"Ya `/userbotjoin` {smallcaps_title('try karo')}.",
                reply_markup=_assistant_invite_keyboard(),
            )

        await status.edit_text(f"🔍 {smallcaps_title('searching on youtube')}...")

        track = await search_track(query)
        if not track:
            return await status.edit_text(f"❌ {smallcaps_title('gaana nahi mila, koi aur naam likho')}.")

        await status.edit_text(f"⏳ {smallcaps_title('gaana load ho raha hai, thoda ruko')}...")

        try:
            stream_url = await get_stream_url(track["id"])
        except Exception as e:
            LOGGER.error(f"Stream URL error: {e}")
            return await status.edit_text(f"❌ {smallcaps_title('audio download error')}: `{e}`")

        track["stream_url"] = stream_url
        track["requested_by"] = requester
        track["requested_by_id"] = requester_id

        if q.is_playing(chat_id):
            position = q.push(chat_id, track)
            await status.delete()
            return await message.reply_text(
                f"🎵 {smallcaps_title('added to queue at')} #{position}\n"
                f"📝 {smallcaps_title('title')} : {track['title']}\n"
                f"🕐 {smallcaps_title('duration')} : {track['duration']}\n"
                f"👤 {smallcaps_title('requested')} : {requester}\n\n"
                f"{CREDIT_LINE}"
            )

        await status.delete()
        await _start_playing(chat_id, track, message)

    except Exception as e:
        LOGGER.error(f"Play command fatal error: {e}")
        try:
            await status.edit_text(f"❌ **Error:** `{e}`")
        except Exception:
            await message.reply_text(f"❌ **Error:** `{e}`")


async def _start_playing(chat_id: int, track: dict, message: Message):
    try:
        await ensure_assistant_started()

        try:
            await call_py.join_group_call(chat_id, AudioPiped(track["stream_url"]))
        except NoActiveGroupCall:
            return await message.reply_text(
                f"❌ **{smallcaps_title('voice chat active nahi hai')}!**\n\n"
                f"{smallcaps_title('pehle group mein voice chat (video chat) start karo, phir')} `/play` {smallcaps_title('bhejo')}."
            )
        except Exception as e:
            err_str = str(e).lower()
            if "already" in err_str or "joined" in err_str:
                try:
                    await call_py.change_stream(chat_id, AudioPiped(track["stream_url"]))
                except Exception as e_change:
                    return await message.reply_text(f"❌ **Stream Change Fail:** `{e_change}`")
            elif "not found" in err_str or "no active" in err_str:
                return await message.reply_text(
                    f"❌ **{smallcaps_title('voice chat active nahi hai')}!**\n\n"
                    f"{smallcaps_title('group mein voice chat start karo, phir play karo')}."
                )
            else:
                try:
                    await call_py.change_stream(chat_id, AudioPiped(track["stream_url"]))
                except Exception as e2:
                    LOGGER.error(f"VC join error: {e2}")
                    return await message.reply_text(
                        f"❌ **{smallcaps_title('voice chat join failed')}!**\n\n"
                        f"`{e2}`\n"
                        f"👉 {smallcaps_title('group voice chat start hai ya nahi check karo aur assistant ko speak permission do')}."
                    )

        q.set_now_playing(chat_id, track)
        await _send_now_playing(chat_id, track, message)

    except Exception as e:
        LOGGER.error(f"_start_playing error: {e}")
        await message.reply_text(f"❌ {smallcaps_title('playback error')}: `{e}`")


def _now_playing_caption(track: dict) -> str:
    artists = [a.strip() for a in str(track.get("channel") or "").replace("-", ",").split(",") if a.strip()]
    if not artists:
        artists = [track.get("requested_by", "Unknown")]

    body = (
        f"» 『 {smallcaps_title(track['title'])} 』\n"
        f"{bullet_lines(smallcaps_title(a) for a in artists)}\n\n"
        f"⌾ {smallcaps_title('duration')} : {track['duration']}\n"
        f"⌾ {smallcaps_title('by')} : {track.get('requested_by', 'Unknown')}\n\n"
        f"{CREDIT_LINE}\n\n"
        f"{DIVIDER}"
    )
    return f"❖ {smallcaps_title('Now Playing')}..!! ✦\n\n" + expandable_quote(body)


async def _send_now_playing(chat_id: int, track: dict, message: Message = None, edit_message: Message = None):
    caption = _now_playing_caption(track)
    card = await generate_now_playing_card(track.get("thumbnail"), track["title"], track["duration"])
    markup = _controls_keyboard()
    media = card or track.get("thumbnail")

    sent = None

    if edit_message is not None:
        try:
            if media:
                sent = await edit_message.edit_media(InputMediaPhoto(media, caption=caption), reply_markup=markup)
            else:
                sent = await edit_message.edit_text(caption, reply_markup=markup, disable_web_page_preview=True)
        except Exception:
            pass

    if sent is None:
        try:
            if media:
                sent = await _safe_quote_send(
                    lambda t: bot.send_photo(chat_id, media, caption=t, reply_markup=markup), caption
                )
            elif message is not None:
                sent = await _safe_quote_send(
                    lambda t: message.reply_text(t, reply_markup=markup, disable_web_page_preview=True), caption
                )
            else:
                sent = await _safe_quote_send(
                    lambda t: bot.send_message(chat_id, t, reply_markup=markup, disable_web_page_preview=True),
                    caption,
                )
        except Exception as e:
            LOGGER.warning(f"Now playing send error: {e}")

    if sent is not None:
        total_sec = duration_to_seconds(track.get("duration"))
        progress.start(chat_id, track["id"])
        progress.start_updater(
            chat_id, sent,
            lambda: _now_playing_caption(track),
            _controls_keyboard,
            track["id"], total_sec,
        )

    return sent


@call_py.on_stream_end()
async def on_stream_end(client, update):
    chat_id = update.chat_id
    next_track = q.pop_next(chat_id)

    if not next_track:
        q.set_now_playing(chat_id, None)
        progress.clear(chat_id)
        try:
            await call_py.leave_group_call(chat_id)
        except Exception:
            pass
        return

    try:
        try:
            await call_py.change_stream(chat_id, AudioPiped(next_track["stream_url"]))
        except Exception:
            await call_py.join_group_call(chat_id, AudioPiped(next_track["stream_url"]))

        q.set_now_playing(chat_id, next_track)
        await _send_now_playing(chat_id, next_track)
    except Exception as e:
        LOGGER.error(f"Auto-play next error: {e}")


@bot.on_message(filters.command(["skip", "cskip"], prefixes=["/", "!", "."]) & filters.group)
async def skip_command(client, message: Message):
    if not await _can_control(client, message.chat.id, message.from_user.id):
        return await message.reply_text(f"❌ {smallcaps_title('sirf requester ya admin skip kar sakte hain')}.")

    chat_id = message.chat.id
    next_track = q.pop_next(chat_id)
    if not next_track:
        q.set_now_playing(chat_id, None)
        progress.clear(chat_id)
        try:
            await call_py.leave_group_call(chat_id)
        except Exception:
            pass
        return await message.reply_text(f"⏭ {smallcaps_title('queue khaali hai, vc se nikal gaya')}.")

    try:
        await call_py.change_stream(chat_id, AudioPiped(next_track["stream_url"]))
    except Exception:
        try:
            await call_py.join_group_call(chat_id, AudioPiped(next_track["stream_url"]))
        except Exception as e2:
            return await message.reply_text(f"❌ {smallcaps_title('skip error')}: `{e2}`")

    q.set_now_playing(chat_id, next_track)
    await _send_now_playing(chat_id, next_track, message)


@bot.on_message(filters.command(["pause", "cpause"], prefixes=["/", "!", "."]) & filters.group)
async def pause_command(client, message: Message):
    if not await _can_control(client, message.chat.id, message.from_user.id):
        return await message.reply_text(f"❌ {smallcaps_title('permission denied')}.")
    try:
        await call_py.pause_stream(message.chat.id)
        q.set_state(message.chat.id, "paused")
        progress.pause(message.chat.id)
        await message.reply_text(f"⏸ {smallcaps_title('playback paused')}.")
    except Exception as e:
        await message.reply_text(f"❌ `{e}`")


@bot.on_message(filters.command(["resume", "cresume"], prefixes=["/", "!", "."]) & filters.group)
async def resume_command(client, message: Message):
    if not await _can_control(client, message.chat.id, message.from_user.id):
        return await message.reply_text(f"❌ {smallcaps_title('permission denied')}.")
    try:
        await call_py.resume_stream(message.chat.id)
        q.set_state(message.chat.id, "playing")
        progress.resume(message.chat.id)
        await message.reply_text(f"▶️ {smallcaps_title('playback resumed')}.")
    except Exception as e:
        await message.reply_text(f"❌ `{e}`")


@bot.on_message(filters.command(["stop", "end", "cstop"], prefixes=["/", "!", "."]) & filters.group)
async def stop_command(client, message: Message):
    if not await _can_control(client, message.chat.id, message.from_user.id):
        return await message.reply_text(f"❌ {smallcaps_title('permission denied')}.")
    try:
        await call_py.leave_group_call(message.chat.id)
    except Exception:
        pass
    q.clear(message.chat.id)
    progress.clear(message.chat.id)
    await message.reply_text(f"⏹️ {smallcaps_title('music stopped & left vc')}.")


@bot.on_message(filters.command(["reload", "refresh"], prefixes=["/", "!", "."]) & filters.group)
async def reload_command(client, message: Message):
    if not await _is_group_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text(f"❌ {smallcaps_title('sirf group admin reload kar sakte hain')}.")
    await message.reply_text(f"✅ {smallcaps_title('bot reloaded successfully')}!\n{CREDIT_LINE}")


@bot.on_callback_query(filters.regex("^m_"))
async def controls_callback(client, cq: CallbackQuery):
    chat_id = cq.message.chat.id
    action = cq.data

    if action in ("m_resume", "m_pause", "m_skip", "m_stop"):
        if not await _can_control(client, chat_id, cq.from_user.id):
            return await cq.answer("❌ Only Requester or Admins can control!", show_alert=True)

    try:
        if action == "m_resume":
            await call_py.resume_stream(chat_id)
            q.set_state(chat_id, "playing")
            progress.resume(chat_id)
            await cq.answer("▶️ Resumed")

        elif action == "m_pause":
            await call_py.pause_stream(chat_id)
            q.set_state(chat_id, "paused")
            progress.pause(chat_id)
            await cq.answer("⏸ Paused")

        elif action == "m_replay":
            track = q.get_now_playing(chat_id)
            if track:
                await call_py.change_stream(chat_id, AudioPiped(track["stream_url"]))
                progress.replay(chat_id)
                await cq.answer("🔁 Replaying")
            else:
                await cq.answer("Kuch nahi baj raha!", show_alert=True)

        elif action == "m_skip":
            await cq.answer("⏭ Skipping")
            next_track = q.pop_next(chat_id)
            if not next_track:
                q.set_now_playing(chat_id, None)
                progress.clear(chat_id)
                await call_py.leave_group_call(chat_id)
                await cq.message.reply_text(f"⏭ {smallcaps_title('queue empty, left vc')}.")
            else:
                await call_py.change_stream(chat_id, AudioPiped(next_track["stream_url"]))
                q.set_now_playing(chat_id, next_track)
                await _send_now_playing(chat_id, next_track, edit_message=cq.message)

        elif action == "m_stop":
            await call_py.leave_group_call(chat_id)
            q.clear(chat_id)
            progress.clear(chat_id)
            await cq.answer("⏹ Stopped")
            await cq.message.reply_text(f"⏹️ {smallcaps_title('music stopped & left vc')}.")

        elif action == "m_close":
            await cq.answer()
            progress.cancel_task(chat_id)
            await cq.message.delete()

    except Exception as e:
        LOGGER.warning(f"Callback error: {e}")
        await cq.answer(f"❌ {e}", show_alert=True)


@bot.on_message(filters.command("id", prefixes=["/", "!", "."]))
async def id_command(client, message: Message):
    user_id = message.from_user.id if message.from_user else "Unknown"
    lines = [f"👤 **{smallcaps_title('your id')}:** `{user_id}`"]
    if message.chat.type != "private":
        lines.append(f"👥 **{smallcaps_title('chat id')}:** `{message.chat.id}`")
    lines.append(f"\n{CREDIT_LINE}")
    await message.reply_text("\n".join(lines))