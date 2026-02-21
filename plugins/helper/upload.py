import asyncio
import time
import os
import json
import mimetypes
import re
import aiohttp
import aiofiles
from pyrogram import Client
from plugins.config import Config

PROGRESS_UPDATE_DELAY = 5  # seconds between progress edits


# ── Formatting helpers ────────────────────────────────────────────────────────

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


# ── FFprobe / FFmpeg helpers ──────────────────────────────────────────────────

async def get_video_metadata(file_path: str) -> dict:
    """
    Use ffprobe (async subprocess) to extract duration, width, height from a video.
    Returns a dict with keys: duration (int seconds), width (int), height (int).
    Falls back to zeros if ffprobe is unavailable or fails.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        data = json.loads(stdout)
        video_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
            None,
        )
        duration = int(float(data.get("format", {}).get("duration", 0)))
        width = int(video_stream.get("width", 0)) if video_stream else 0
        height = int(video_stream.get("height", 0)) if video_stream else 0
        return {"duration": duration, "width": width, "height": height}
    except Exception:
        return {"duration": 0, "width": 0, "height": 0}


async def generate_video_thumbnail(file_path: str, chat_id: int, duration: int = 0) -> str | None:
    """
    Extract a single frame from the video at 10% of its duration (or 1 s if unknown),
    scaled to max width 320 px, saved as JPEG.  Returns the path or None on failure.
    """
    thumb_path = os.path.join(Config.DOWNLOAD_LOCATION, f"thumb_auto_{chat_id}.jpg")
    # Pick a timestamp: 10% into the video, minimum 1 s
    seek = max(1, int(duration * 0.1)) if duration else 1
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-ss", str(seek),
            "-i", file_path,
            "-vframes", "1",
            "-vf", "scale=320:-1",
            "-q:v", "2",          # JPEG quality (2 = very high, 31 = worst)
            thumb_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=60)
        if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
            return thumb_path
    except Exception:
        pass
    return None


# ── Download helper ───────────────────────────────────────────────────────────

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
        async with session.get(
            url,
            allow_redirects=True,
            timeout=aiohttp.ClientTimeout(total=Config.PROCESS_MAX_TIMEOUT),
        ) as resp:
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


# ── Upload helper ─────────────────────────────────────────────────────────────

async def upload_file(
    client: Client,
    chat_id: int,
    file_path: str,
    mime: str,
    caption: str,
    thumb_file_id: str | None,
    progress_msg,
    start_time_ref: list,
):
    """
    Upload a local file to Telegram with:
    - Live progress bar
    - Correct duration / width / height for videos (extracted via ffprobe)
    - Auto-generated thumbnail from the video frame if no custom thumb is set
    - Custom thumbnail (downloaded from Telegram by file_id) if set by user
    """

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

    os.makedirs(Config.DOWNLOAD_LOCATION, exist_ok=True)
    is_video = mime and mime.startswith("video/")

    # ── 1. Get video metadata (duration, width, height) ───────────────────────
    meta = {"duration": 0, "width": 0, "height": 0}
    if is_video:
        try:
            await progress_msg.edit_text("🔍 Reading video metadata…")
        except Exception:
            pass
        meta = await get_video_metadata(file_path)

    # ── 2. Resolve thumbnail ───────────────────────────────────────────────────
    thumb_local = None
    auto_thumb = False

    if thumb_file_id:
        # User has a saved thumbnail — download it from Telegram
        try:
            thumb_local = await client.download_media(
                thumb_file_id,
                file_name=os.path.join(Config.DOWNLOAD_LOCATION, f"thumb_user_{chat_id}.jpg"),
            )
        except Exception:
            thumb_local = None

    if not thumb_local and is_video:
        # No custom thumb → auto-generate from video frame
        try:
            await progress_msg.edit_text("🖼️ Generating thumbnail…")
        except Exception:
            pass
        thumb_local = await generate_video_thumbnail(file_path, chat_id, meta["duration"])
        auto_thumb = True

    # ── 3. Build kwargs (chat_id and file passed as positional args) ───────────
    kwargs = dict(
        caption=caption,
        parse_mode=None,
        progress=_progress,
    )
    if thumb_local:
        kwargs["thumb"] = thumb_local

    # ── 4. Send to Telegram ───────────────────────────────────────────────────
    try:
        if is_video:
            await client.send_video(
                chat_id,
                file_path,
                duration=meta["duration"],
                width=meta["width"],
                height=meta["height"],
                supports_streaming=True,   # marks the video as streamable
                **kwargs,
            )
        elif mime and mime.startswith("audio/"):
            await client.send_audio(chat_id, file_path, **kwargs)
        elif mime and mime.startswith("image/"):
            await client.send_photo(chat_id, file_path,
                                    caption=caption, progress=_progress)
        else:
            await client.send_document(chat_id, file_path, **kwargs)
    finally:
        # Clean up any temp thumbnail files
        if thumb_local and os.path.exists(thumb_local):
            try:
                os.remove(thumb_local)
            except Exception:
                pass
