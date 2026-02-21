import asyncio
import os
import re
import time
import urllib.parse
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from plugins.config import Config
from plugins.helper.database import add_user, get_user, update_user, is_banned
from plugins.helper.upload import download_url, upload_file, humanbytes

# ─────────────────────────────────────────────────────────────────────────────
# In-memory state for pending renames  {user_id: {"url": str, "orig": str}}
# ─────────────────────────────────────────────────────────────────────────────
PENDING_RENAMES: dict[int, dict] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_filename(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    name = os.path.basename(parsed.path.rstrip("/"))
    return urllib.parse.unquote(name) if name else "downloaded_file"


def is_owner_or_admin(user_id: int) -> bool:
    return user_id == Config.OWNER_ID or user_id in Config.ADMIN


HELP_TEXT = """
📋 **Bot Commands**

➤ /start – Check if the bot is alive 🔔
➤ /help – Show this help message ❓
➤ /about – Info about the bot ℹ️
➤ /upload `<url>` – Upload a file from a direct URL 📤
➤ /skip – Keep original filename (use after /upload)

**Caption:**
➤ /caption `<text>` – Set a custom caption for uploads 📝
➤ /showcaption – View your current caption
➤ /clearcaption – Remove your custom caption

**Thumbnail:**
➤ /setthumb – Reply to a photo to set thumbnail 🖼️
➤ /showthumb – View your current thumbnail
➤ /delthumb – Delete your saved thumbnail

**Admin only:**
➤ /broadcast `<msg>` – Broadcast to all users 📢
➤ /total – Total registered users 👥
➤ /ban `<id>` – Ban a user ⛔
➤ /unban `<id>` – Unban a user ✅
➤ /status – Bot resource usage 🚀
"""

ABOUT_TEXT = """
🤖 **URL Uploader Bot**

Upload files up to **2 GB** directly to Telegram from any direct URL.

**Features:**
• ✏️ Rename files before upload
• 🖼️ Permanent thumbnails (saved to your account)
• 📝 Custom captions
• 📊 Live progress bars

**Tech:** Pyrogram MTProto · MongoDB · Docker · Koyeb
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Core Upload Logic (shared by /upload and auto-URL handler)
# ─────────────────────────────────────────────────────────────────────────────

async def do_upload(client: Client, message: Message, url: str, filename: str):
    """Download from URL and upload to Telegram."""
    user = message.from_user
    status_msg = await message.reply_text(
        f"📥 Starting download…\n📁 `{filename}`", quote=True
    )
    start_time = [time.time()]
    file_path = None
    try:
        file_path, mime = await download_url(url, filename, status_msg, start_time)
        file_size = os.path.getsize(file_path)

        # ── User settings ──────────────────────────────────────
        user_data = await get_user(user.id) or {}
        custom_caption = user_data.get("caption") or ""
        thumb_file_id = user_data.get("thumb") or None   # stored as Telegram file_id

        caption = (
            custom_caption
            or f"📁 **{os.path.basename(file_path)}**\n💾 {humanbytes(file_size)}"
        )

        await status_msg.edit_text("📤 Uploading to Telegram…")
        await upload_file(
            client, message.chat.id, file_path, mime,
            caption, thumb_file_id, status_msg, start_time
        )
        await status_msg.edit_text("✅ Upload complete!")

        # ── Log ────────────────────────────────────────────────
        if Config.LOG_CHANNEL:
            elapsed = time.time() - start_time[0]
            try:
                await client.send_message(
                    Config.LOG_CHANNEL,
                    f"📤 **Upload log**\n"
                    f"👤 {user.mention} (`{user.id}`)\n"
                    f"🔗 `{url}`\n"
                    f"📁 `{os.path.basename(file_path)}`\n"
                    f"💾 {humanbytes(file_size)} · ⏱ {elapsed:.1f}s",
                )
            except Exception:
                pass

    except ValueError as e:
        await status_msg.edit_text(f"❌ {e}")
    except Exception as e:
        Config.LOGGER.exception("Upload error")
        await status_msg.edit_text(f"❌ Error: `{e}`")
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
#  /start
# ─────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user = message.from_user
    await add_user(user.id, user.username)
    if await is_banned(user.id):
        return await message.reply_text("🚫 You are banned from using this bot.")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Updates", url=f"https://t.me/{Config.UPDATES_CHANNEL}")],
        [InlineKeyboardButton("❓ Help", callback_data="help"),
         InlineKeyboardButton("ℹ️ About", callback_data="about")],
    ])
    await message.reply_text(
        f"👋 Hello **{user.first_name}**!\n\n"
        "I can upload files up to **2 GB** to Telegram from any direct URL.\n\n"
        "📤 Send a URL or use `/upload <url>` to get started!\n"
        "✏️ I'll ask if you want to **rename** the file before uploading.",
        reply_markup=kb,
        quote=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  /help  /about  — callback buttons
# ─────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("help") & filters.private)
async def help_handler(client: Client, message: Message):
    await message.reply_text(HELP_TEXT, quote=True)


@Client.on_message(filters.command("about") & filters.private)
async def about_handler(client: Client, message: Message):
    await message.reply_text(ABOUT_TEXT, quote=True)


@Client.on_callback_query()
async def cb_handler(client, callback_query):
    data = callback_query.data
    if data == "help":
        await callback_query.message.edit_text(HELP_TEXT)
    elif data == "about":
        await callback_query.message.edit_text(ABOUT_TEXT)


# ─────────────────────────────────────────────────────────────────────────────
#  /upload <url>  — step 1: ask for rename
# ─────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("upload") & filters.private)
async def upload_handler(client: Client, message: Message):
    user = message.from_user
    await add_user(user.id, user.username)

    if await is_banned(user.id):
        return await message.reply_text("🚫 You are banned.")

    args = message.command
    url = None
    if len(args) > 1:
        url = args[1].strip()
    elif message.reply_to_message and message.reply_to_message.text:
        url = message.reply_to_message.text.strip()

    if not url or not url.startswith(("http://", "https://")):
        return await message.reply_text(
            "❌ Please provide a valid direct URL.\n\nUsage: `/upload https://example.com/file.mp4`",
            quote=True,
        )

    orig_filename = extract_filename(url)
    PENDING_RENAMES[user.id] = {"url": url, "orig": orig_filename}

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ Skip (keep original)", callback_data=f"skip_rename:{user.id}")]
    ])
    await message.reply_text(
        f"✏️ **Rename file?**\n\n"
        f"📁 Original: `{orig_filename}`\n\n"
        "Send the **new filename** (with extension) or press **Skip** to keep the original:",
        reply_markup=kb,
        quote=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  /skip — keep original filename
# ─────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("skip") & filters.private)
async def skip_handler(client: Client, message: Message):
    user_id = message.from_user.id
    pending = PENDING_RENAMES.pop(user_id, None)
    if not pending:
        return await message.reply_text("❌ No pending upload. Send a URL first.", quote=True)
    await do_upload(client, message, pending["url"], pending["orig"])


# ─────────────────────────────────────────────────────────────────────────────
#  Inline "Skip" button handler
# ─────────────────────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^skip_rename:(\d+)$"))
async def skip_rename_cb(client, callback_query):
    user_id = callback_query.from_user.id
    target_id = int(callback_query.data.split(":")[1])
    if user_id != target_id:
        return await callback_query.answer("Not your upload!", show_alert=True)
    pending = PENDING_RENAMES.pop(user_id, None)
    if not pending:
        return await callback_query.answer("Already processed or expired.", show_alert=True)
    await callback_query.message.edit_text(f"⏭ Keeping original: `{pending['orig']}`")
    await do_upload(client, callback_query.message, pending["url"], pending["orig"])


# ─────────────────────────────────────────────────────────────────────────────
#  Handle text messages in private — rename input OR bare URL
# ─────────────────────────────────────────────────────────────────────────────

_ALL_COMMANDS = [
    "start", "help", "about", "upload", "skip", "caption", "showcaption",
    "clearcaption", "setthumb", "showthumb", "delthumb",
    "broadcast", "total", "ban", "unban", "status",
]


@Client.on_message(filters.private & filters.text & ~filters.command(_ALL_COMMANDS))
async def text_handler(client: Client, message: Message):
    user = message.from_user
    text = (message.text or "").strip()

    # ── Pending rename input ──────────────────────────────────
    if user.id in PENDING_RENAMES:
        pending = PENDING_RENAMES.pop(user.id)
        new_name = text.strip()
        # Preserve original extension if user didn't include one
        orig_ext = os.path.splitext(pending["orig"])[1]
        new_ext = os.path.splitext(new_name)[1]
        if not new_ext and orig_ext:
            new_name = new_name + orig_ext
        await message.reply_text(f"✏️ Renamed to: `{new_name}`", quote=True)
        await do_upload(client, message, pending["url"], new_name)
        return

    # ── Bare URL ──────────────────────────────────────────────
    if text.startswith(("http://", "https://")):
        await add_user(user.id, user.username)
        if await is_banned(user.id):
            return await message.reply_text("🚫 You are banned.")
        orig_filename = extract_filename(text)
        PENDING_RENAMES[user.id] = {"url": text, "orig": orig_filename}
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭ Skip (keep original)", callback_data=f"skip_rename:{user.id}")]
        ])
        await message.reply_text(
            f"✏️ **Rename file?**\n\n"
            f"📁 Original: `{orig_filename}`\n\n"
            "Send the **new filename** (with extension) or press **Skip**:",
            reply_markup=kb,
            quote=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Caption management
# ─────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("caption") & filters.private)
async def set_caption(client: Client, message: Message):
    args = message.command
    if len(args) < 2:
        return await message.reply_text("Usage: `/caption Your caption text here`", quote=True)
    caption = " ".join(args[1:])
    await update_user(message.from_user.id, {"caption": caption})
    await message.reply_text(f"✅ Caption saved:\n\n{caption}", quote=True)


@Client.on_message(filters.command("showcaption") & filters.private)
async def show_caption(client: Client, message: Message):
    user_data = await get_user(message.from_user.id) or {}
    cap = user_data.get("caption") or "_(none set)_"
    await message.reply_text(f"📝 Your caption:\n\n{cap}", quote=True)


@Client.on_message(filters.command("clearcaption") & filters.private)
async def clear_caption(client: Client, message: Message):
    await update_user(message.from_user.id, {"caption": ""})
    await message.reply_text("✅ Caption cleared.", quote=True)


# ─────────────────────────────────────────────────────────────────────────────
#  Thumbnail management  — stored as Telegram file_id (permanent)
# ─────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("setthumb") & filters.private)
async def set_thumb(client: Client, message: Message):
    reply = message.reply_to_message
    if not reply or not reply.photo:
        return await message.reply_text(
            "❌ Reply to a **photo** with /setthumb to save it as your thumbnail.",
            quote=True,
        )
    # Use the largest available size and store its file_id (Telegram-permanent)
    photo = reply.photo
    file_id = photo.file_id
    await update_user(message.from_user.id, {"thumb": file_id})
    await message.reply_text(
        "✅ Thumbnail saved permanently!\n"
        "It will be applied to all your future uploads.",
        quote=True,
    )


@Client.on_message(filters.command("showthumb") & filters.private)
async def show_thumb(client: Client, message: Message):
    user_data = await get_user(message.from_user.id) or {}
    thumb_id = user_data.get("thumb")
    if not thumb_id:
        return await message.reply_text("❌ No thumbnail set. Reply to a photo with /setthumb.", quote=True)
    try:
        await message.reply_photo(photo=thumb_id, caption="🖼️ Your current thumbnail", quote=True)
    except Exception as e:
        await message.reply_text(f"❌ Could not show thumbnail: `{e}`", quote=True)


@Client.on_message(filters.command("delthumb") & filters.private)
async def del_thumb(client: Client, message: Message):
    await update_user(message.from_user.id, {"thumb": None})
    await message.reply_text("✅ Thumbnail deleted.", quote=True)
