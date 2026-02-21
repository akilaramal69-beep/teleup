import os
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
    level=logging.INFO,
)


class Config:
    # ── Telegram ──────────────────────────────────────
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
    API_ID: int = int(os.environ.get("API_ID", 0))
    API_HASH: str = os.environ.get("API_HASH", "")
    BOT_USERNAME: str = os.environ.get("BOT_USERNAME", "UrlUploaderBot")

    # ── Owner / Admins ────────────────────────────────
    OWNER_ID: int = int(os.environ.get("OWNER_ID", 0))
    ADMIN: set = set(
        int(x) for x in os.environ.get("ADMIN", "").split() if x.isdigit()
    )
    BANNED_USERS: set = set(
        int(x) for x in os.environ.get("BANNED_USERS", "").split() if x.isdigit()
    )

    # ── Channels ──────────────────────────────────────
    LOG_CHANNEL: int = int(os.environ.get("LOG_CHANNEL", 0))
    UPDATES_CHANNEL: str = os.environ.get("UPDATES_CHANNEL", "")

    # ── Database ──────────────────────────────────────
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")

    # ── File handling ─────────────────────────────────
    DOWNLOAD_LOCATION: str = "./DOWNLOADS"
    MAX_FILE_SIZE: int = 2_097_152_000          # ~2 GB (Pyrogram MTProto limit)
    CHUNK_SIZE: int = int(os.environ.get("CHUNK_SIZE", 512)) * 1024  # KB → bytes

    # ── Misc ──────────────────────────────────────────
    LOGGER = logging
    DEF_WATER_MARK_FILE: str = "@" + BOT_USERNAME
    PROCESS_MAX_TIMEOUT: int = 3600
    SESSION_STRING: str = os.environ.get("SESSION_STRING", "")  # optional premium session for 4 GB
