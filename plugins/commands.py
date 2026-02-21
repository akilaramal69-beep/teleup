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

# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_filename(url: str, content_disposition: str | None = None) -> str:
    if content_disposition:
        match = re.search(r'filename\*?=["\']?(?:UTF-\d[\'"]*)?([^;\r\n"\']+)', content_disposition)
        if match:
            return urllib.parse.unquote(match.group(1).strip())
    parsed = urllib.parse.urlparse(url)
    name = os.path.basename(parsed.path)
    return name if name else "downloaded_file"


def is_owner_or_admin(user_id: int) -> bool:
    return user_id == Config.OWNER_ID or user_id in Config.ADMIN


HELP_TEXT = """
📋 **Bot Commands**

➤ /start – Check if the bot is alive 🔔
➤ /help – Show this help message ❓
➤ /about – Info about the bot ℹ️
➤ /upload `<url>` – Upload a file from a direct URL 📤
➤ /caption `<text>` – Set a custom caption for uploads 📝
➤ /showcaption – View your current caption
➤ /clearcaption – Remove your custom caption
➤ /setthumb – Reply to a photo with this to set thumbnail 🖼️
➤ /showthumb – View your current thumbnail
➤ /delthumb – Delete your thumbnail

**Admin only:**
➤ /broadcast `<message>` – Broadcast to all users 📢
➤ /total – Total registered users 👥
➤ /ban `<user_id>` – Ban a user ⛔
➤ /unban `<user_id>` – Unban a user ✅
➤ /status – Bot status 🚀
"""

ABOUT_TEXT = """
🤖 **URL Uploader Bot**

Upload files up to **2 GB** directly to Telegram from any direct download URL.

**Tech Stack:**
• [Pyrogram](https://docs.pyrogram.org/) (MTProto — enables 2 GB uploads)
• Python 3.11
• MongoDB (user data)
• Docker + Koyeb (deployment)

**Source:** Open source — feel free to fork!
"""

# ── /start ────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user = message.from_user
    await add_user(user.id, user.username)
    if await is_banned(user.id):
        return await message.reply_text("🚫 You are banned from using this bot.")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Updates Channel", url=f"https://t.me/{Config.UPDATES_CHANNEL}")],
        [InlineKeyboardButton("❓ Help", callback_data="help"),
         InlineKeyboardButton("ℹ️ About", callback_data="about")],
    ])
    await message.reply_text(
        f"👋 Hello **{user.first_name}**!\n\n"
        "I can upload files up to **2 GB** to Telegram from any direct URL.\n\n"
        "Send me a direct download link or use /upload `<url>` to get started! 🚀",
        reply_markup=kb,
        quote=True,
    )


# ── /help ─────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("help") & filters.private)
async def help_handler(client: Client, message: Message):
    await message.reply_text(HELP_TEXT, quote=True)


# ── /about ────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("about") & filters.private)
async def about_handler(client: Client, message: Message):
    await message.reply_text(ABOUT_TEXT, quote=True)


# ── Callback buttons (inline keyboard) ───────────────────────────────────────

@Client.on_callback_query()
async def cb_handler(client, callback_query):
    data = callback_query.data
    if data == "help":
        await callback_query.message.edit_text(HELP_TEXT)
    elif data == "about":
        await callback_query.message.edit_text(ABOUT_TEXT)


# ── /upload ───────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("upload") & filters.private)
async def upload_handler(client: Client, message: Message):
    user = message.from_user
    await add_user(user.id, user.username)

    if await is_banned(user.id):
        return await message.reply_text("🚫 You are banned.")

    # Parse URL from command args or replied message
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

    status_msg = await message.reply_text("🔍 Fetching file info…", quote=True)

    start_time = [time.time()]
    try:
        # ── Download ──────────────────────────────────────
        filename = extract_filename(url)
        await status_msg.edit_text(f"📥 Starting download of `{filename}`…")
        file_path, mime = await download_url(url, filename, status_msg, start_time)

        file_size = os.path.getsize(file_path)

        # ── Retrieve user settings ────────────────────────
        user_data = await get_user(user.id) or {}
        custom_caption = user_data.get("caption") or ""
        thumb_path = user_data.get("thumb") or None
        caption = (
            custom_caption
            or f"📁 **{os.path.basename(file_path)}**\n💾 Size: {humanbytes(file_size)}"
        )

        # ── Upload ────────────────────────────────────────
        await status_msg.edit_text("📤 Uploading to Telegram…")
        await upload_file(client, message.chat.id, file_path, mime, caption, thumb_path, status_msg, start_time)
        await status_msg.edit_text("✅ Upload complete!")

        # ── Log to channel ───────────────────────────────
        if Config.LOG_CHANNEL:
            elapsed = time.time() - start_time[0]
            try:
                await client.send_message(
                    Config.LOG_CHANNEL,
                    f"📤 **Upload log**\n"
                    f"👤 User: {user.mention} (`{user.id}`)\n"
                    f"🔗 URL: `{url}`\n"
                    f"💾 Size: {humanbytes(file_size)}\n"
                    f"⏱ Time: {elapsed:.1f}s",
                )
            except Exception:
                pass

    except ValueError as e:
        await status_msg.edit_text(f"❌ {e}")
    except Exception as e:
        Config.LOGGER.exception("Upload error")
        await status_msg.edit_text(f"❌ Error: `{e}`")
    finally:
        try:
            if "file_path" in dir() and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass


# ── Handle bare URLs in private chat ─────────────────────────────────────────

@Client.on_message(filters.private & filters.text & ~filters.command(["start", "help", "about",
    "upload", "caption", "showcaption", "clearcaption", "setthumb", "showthumb", "delthumb",
    "broadcast", "total", "ban", "unban", "status"]))
async def auto_url_handler(client: Client, message: Message):
    text = (message.text or "").strip()
    if text.startswith(("http://", "https://")):
        # Re-use upload handler
        message.command = ["upload", text]
        await upload_handler(client, message)


# ── /caption ──────────────────────────────────────────────────────────────────

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


# ── Thumbnail management ──────────────────────────────────────────────────────

@Client.on_message(filters.command("setthumb") & filters.private)
async def set_thumb(client: Client, message: Message):
    reply = message.reply_to_message
    if not reply or not reply.photo:
        return await message.reply_text("❌ Reply to a **photo** with /setthumb.", quote=True)
    thumb_file = await reply.download(file_name=f"./DOWNLOADS/thumb_{message.from_user.id}.jpg")
    await update_user(message.from_user.id, {"thumb": thumb_file})
    await message.reply_text("✅ Thumbnail saved!", quote=True)


@Client.on_message(filters.command("showthumb") & filters.private)
async def show_thumb(client: Client, message: Message):
    user_data = await get_user(message.from_user.id) or {}
    thumb = user_data.get("thumb")
    if not thumb or not os.path.exists(thumb):
        return await message.reply_text("❌ No thumbnail set.", quote=True)
    await message.reply_photo(photo=thumb, caption="🖼️ Your current thumbnail", quote=True)


@Client.on_message(filters.command("delthumb") & filters.private)
async def del_thumb(client: Client, message: Message):
    user_data = await get_user(message.from_user.id) or {}
    thumb = user_data.get("thumb")
    if thumb and os.path.exists(thumb):
        os.remove(thumb)
    await update_user(message.from_user.id, {"thumb": None})
    await message.reply_text("✅ Thumbnail deleted.", quote=True)
