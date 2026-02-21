import asyncio
import time
import math
import os
import mimetypes
import re
import aiohttp
import aiofiles
from pyrogram import Client
from plugins.config import Config

PROGRESS_UPDATE_DELAY = 5  # seconds between progress edits


def humanbytes(size: int) -> str:
    if not size:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def time_formatter(seconds: float) -> str:
    minutes, sec = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {sec}s"
    elif minutes:
        return f"{minutes}m {sec}s"
    return f"{sec}s"


def progress_bar(current: int, total: int, length: int = 12) -> str:
    filled = int(length * current / total) if total else 0
    bar = "█" * filled + "░" * (length - filled)
    percent = current / total * 100 if total else 0
    return f"[{bar}] {percent:.1f}%"


async def download_url(url: str, filename: str, progress_msg, start_time_ref: list):
    """
    Stream-download a URL to disk, editing progress_msg periodically.
    Returns (path, mime_type) on success or raises.
    """
    download_dir = Config.DOWNLOAD_LOCATION
    os.makedirs(download_dir, exist_ok=True)

    safe_name = re.sub(r'[\\/*?:"<>|]', "_", filename)[:200]
    file_path = os.path.join(download_dir, safe_name)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    last_edit = time.time()
    start_time_ref[0] = time.time()

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=Config.PROCESS_MAX_TIMEOUT)) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length", 0))
            mime = resp.content_type or "application/octet-stream"
            if total > Config.MAX_FILE_SIZE:
                raise ValueError(
                    f"File too large: {humanbytes(total)} (max {humanbytes(Config.MAX_FILE_SIZE)})"
                )
            downloaded = 0
            async with aiofiles.open(file_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(Config.CHUNK_SIZE):
                    await f.write(chunk)
                    downloaded += len(chunk)
                    now = time.time()
                    if now - last_edit >= PROGRESS_UPDATE_DELAY:
                        elapsed = now - start_time_ref[0]
                        speed = downloaded / elapsed if elapsed else 0
                        eta = (total - downloaded) / speed if speed and total else 0
                        bar = progress_bar(downloaded, total)
                        text = (
                            "📥 **Downloading…**\n\n"
                            f"{bar}\n"
                            f"**Done:** {humanbytes(downloaded)}"
                            + (f" / {humanbytes(total)}" if total else "")
                            + f"\n**Speed:** {humanbytes(speed)}/s\n"
                            f"**ETA:** {time_formatter(eta)}"
                        )
                        try:
                            await progress_msg.edit_text(text)
                        except Exception:
                            pass
                        last_edit = now

    mime_from_ext = mimetypes.guess_type(file_path)[0]
    final_mime = mime_from_ext or mime
    return file_path, final_mime


async def upload_file(client: Client, chat_id: int, file_path: str, mime: str,
                      caption: str, thumb: str | None, progress_msg, start_time_ref: list):
    """Upload a local file to Telegram with live progress."""

    last_edit = [time.time()]
    start_time_ref[0] = time.time()

    async def _progress(current: int, total: int):
        now = time.time()
        if now - last_edit[0] < PROGRESS_UPDATE_DELAY:
            return
        elapsed = now - start_time_ref[0]
        speed = current / elapsed if elapsed else 0
        eta = (total - current) / speed if speed else 0
        bar = progress_bar(current, total)
        text = (
            "📤 **Uploading…**\n\n"
            f"{bar}\n"
            f"**Done:** {humanbytes(current)} / {humanbytes(total)}\n"
            f"**Speed:** {humanbytes(speed)}/s\n"
            f"**ETA:** {time_formatter(eta)}"
        )
        try:
            await progress_msg.edit_text(text)
        except Exception:
            pass
        last_edit[0] = now

    kwargs = dict(
        chat_id=chat_id,
        caption=caption,
        parse_mode=None,
        progress=_progress,
    )
    if thumb:
        kwargs["thumb"] = thumb

    if mime and mime.startswith("video/"):
        await client.send_video(file_path, **kwargs)
    elif mime and mime.startswith("audio/"):
        await client.send_audio(file_path, **kwargs)
    elif mime and mime.startswith("image/"):
        await client.send_photo(chat_id=chat_id, photo=file_path,
                                 caption=caption, progress=_progress)
    else:
        await client.send_document(file_path, **kwargs)
