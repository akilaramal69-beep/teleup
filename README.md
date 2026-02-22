# 🤖 Telegram URL Uploader Bot

Upload files up to **2 GB** to Telegram from any URL — including YouTube, Instagram, TikTok and 700+ more platforms. Built with [Pyrogram](https://docs.pyrogram.org/) (MTProto) for large file support, deployable on **Koyeb**.

---

## ✨ Features

| Feature | Details |
|---|---|
| 📤 Direct URL Upload | Send any direct download URL — bot downloads & uploads |
| 📺 yt-dlp Integration | Download from YouTube, Instagram, TikTok, Twitter/X, Reddit, Vimeo, Twitch, SoundCloud, Bilibili + 700 more |
| 🎚️ Dynamic Quality Selector | Auto-detects available resolutions — shows 360p / 480p / 720p / 1080p / Best for video sources |
| 🎧 Audio-Only Mode | Audio-only sources (SoundCloud, etc.) automatically show **Best Audio** + **MP3** buttons |
| 🎵 MP3 Extraction | Extract audio as MP3 (192 kbps) from any yt-dlp URL |
| ✏️ File Renaming | Bot asks for a new filename before every upload |
| 🎬 Media / Document Mode | Choose to send as streamable video or raw document (direct links) |
| 🎞️ Auto Thumbnail | ffmpeg auto-generates thumbnail from video frame |
| ⏱️ Video Metadata | ffprobe extracts duration, width, height for proper Telegram video display |
| 🌊 HLS / DASH Streams | `.m3u8`, `.mpd`, `.ts` streamed via ffmpeg → saved as `.mp4` |
| 💾 Up to 2 GB | Pyrogram MTProto — not the 50 MB Bot API limit |
| 🚀 Upload Boost | pyroblack with `upload_boost=True` + parallel MTProto connections |
| 📝 Custom Captions | Per-user saved captions |
| 🖼️ Permanent Thumbnails | Stored as Telegram `file_id` — survive restarts & redeployments |
| 📊 Live Progress | Download & upload progress bars with speed and ETA |
| 🍪 Cookie Support | Pass `YT_COOKIES_B64` env var to bypass YouTube bot detection |
| 🔑 Auto PO Token | Integrated [bgutil](https://github.com/Brainicism/bgutil-ytdlp-pot-provider) — auto-generates YouTube PO tokens in Docker |
| 📢 Broadcast | Send messages to all users (admin) |
| 🚫 Ban / Unban | User management (admin) |
| ☁️ Koyeb Ready | Docker + Flask health server on port 8080 |

---

## 🌐 Supported Platforms (yt-dlp)

YouTube · Instagram · Twitter / X · TikTok · Facebook · Reddit · Vimeo · Dailymotion · Twitch · SoundCloud · Bilibili · Rumble · Odysee · Streamable · Mixcloud · Pinterest + [700 more](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

---

## 📥 Upload Flow

### For yt-dlp URLs — Video sources (YouTube, etc.)
```
Send URL
  → 🔍 Fetching video info…
  → ✏️ Rename? (or skip)
  → Quality selector (buttons adapt to available resolutions):
      [ 360p ] [ 480p ] [ 720p 📺 ]
      [ 1080p ⭐ ] [ 🏆 Best ] [ 🎧 MP3 ]
  → Download + Upload
```

### For yt-dlp URLs — Audio-only sources (SoundCloud, etc.)
```
Send URL
  → 🔍 Fetching info…
  → ✏️ Rename? (or skip)
  → Quality selector:
      [ 🎵 Best Audio ] [ 🎧 MP3 (192k) ]
  → Download + Upload
```

### For direct file links (.mp4, .zip, etc.)
```
Send URL
  → ✏️ Rename? (or skip)
  → [ 🎬 Media ]  [ 📄 Document ]
  → Download + Upload
```

---

## 🚀 Bot Commands

```
/start           – Check if bot is alive 🔔
/help            – Show all commands ❓
/about           – Bot info ℹ️
/upload <url>    – Upload file from URL 📤
/skip            – Keep original filename during rename

/caption <text>  – Set custom upload caption 📝
/showcaption     – View your caption
/clearcaption    – Clear caption

/setthumb        – Reply to a photo to set permanent thumbnail 🖼️
/showthumb       – Preview your thumbnail
/delthumb        – Delete thumbnail

--- Admin only ---
/broadcast <msg> – Broadcast to all users 📢
/total           – Total registered users 👥
/ban <id>        – Ban a user ⛔
/unban <id>      – Unban a user ✅
/status          – CPU / RAM / disk usage 🚀
```

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | From [@BotFather](https://t.me/BotFather) |
| `API_ID` | ✅ | From [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | ✅ | From [my.telegram.org](https://my.telegram.org) |
| `OWNER_ID` | ✅ | Your Telegram user ID |
| `DATABASE_URL` | ✅ | MongoDB Atlas connection string |
| `LOG_CHANNEL` | ✅ | Private channel ID for upload logs |
| `BOT_USERNAME` | ⬜ | Bot username (without @) |
| `UPDATES_CHANNEL` | ⬜ | Updates channel username |
| `ADMIN` | ⬜ | Space-separated admin user IDs |
| `SESSION_STRING` | ⬜ | Pyrogram session string (4 GB uploads) |
| `CHUNK_SIZE` | ⬜ | Download chunk size in KB (default: 512) |
| `YT_COOKIES_B64` | ⬜ | Base64-encoded `cookies.txt` — helps with age-restricted / member-only YouTube content |
| `COOKIES_FILE` | ⬜ | Path to a local `cookies.txt` file (alternative to above) |
| `YT_POTOKEN` | ⬜ | YouTube Proof-of-Origin token — only needed if **not** using Docker (Docker auto-generates via bgutil) |

### 🔑 YouTube PO Token (Docker — automatic)

When running via Docker (**Koyeb recommended**), the Dockerfile automatically:
- Installs Node.js 20
- Clones the [bgutil POT provider](https://github.com/Brainicism/bgutil-ytdlp-pot-provider) server
- Starts the POT HTTP server on port `4416` alongside the bot
- yt-dlp auto-discovers the plugin and fetches fresh tokens — **no manual setup needed**

You can verify it's working by checking Koyeb logs for:
```
[debug] [youtube] [pot] PO Token Providers: bgutil:http-1.2.2 (external)
```

### 🍪 YouTube Cookies (`YT_COOKIES_B64`) — optional

Cookies help with age-restricted or members-only content. PO tokens handle general bot detection.

1. Install **"Get cookies.txt LOCALLY"** browser extension
2. Go to **youtube.com** while logged in → click extension → **Export**
3. Encode the file:
   - **PowerShell:** `[Convert]::ToBase64String([IO.File]::ReadAllBytes("cookies.txt")) | clip`
   - **Linux/Mac:** `base64 -w 0 cookies.txt`
4. Paste the output as `YT_COOKIES_B64` in Koyeb environment variables

---

## 🐳 Local Setup

```bash
git clone https://github.com/YOUR_USERNAME/tg-url-uploader.git
cd tg-url-uploader

cp .env.example .env
# Fill in your values in .env

pip install -r requirements.txt
python bot.py
```

> **Requires:** `ffmpeg` and `ffprobe` installed on the system (included in the Docker image).

> **Note:** When running locally without Docker, the bgutil PO Token server won't start automatically. Either run it manually (`node /path/to/bgutil/server/build/main.js`) or set `YT_POTOKEN` manually.

---

## ☁️ Deploy to Koyeb

### Method 1 — Docker (recommended)

1. Fork this repo on GitHub
2. Go to [koyeb.com](https://www.koyeb.com) → **Create Service** → **Docker**
3. Use **GitHub** source and enable Docker build
4. Add all required environment variables
5. Set **Port** to `8080` (health check at `/health`)
6. Deploy! ✅

The Docker image automatically builds the bgutil POT server — no extra configuration needed.

### Method 2 — GitHub + Buildpack

1. Connect your GitHub repo to Koyeb
2. Build Command: `pip install -r requirements.txt`
3. Run Command: `python bot.py`
4. Port: `8080`
5. Add env vars → Deploy ✅

> ⚠️ Buildpack mode won't have Node.js available, so the bgutil auto-token won't work. Set `YT_POTOKEN` manually in this case.

---

## 📁 Project Structure

```
tg-url-uploader/
├── bot.py                  # Entrypoint (Pyrogram + Flask thread)
├── app.py                  # Flask health server (port 8080)
├── requirements.txt
├── Dockerfile              # Includes Node.js + bgutil POT server
├── .env.example
└── plugins/
    ├── config.py           # Config from env vars + cookie/token resolver
    ├── commands.py         # User commands + rename/quality/mode flow
    ├── admin.py            # Admin commands
    └── helper/
        ├── upload.py       # Download (aiohttp/yt-dlp/ffmpeg) + upload logic
        └── database.py     # MongoDB async helper
```

---

## 📝 Notes

- **2 GB limit** via Pyrogram's MTProto API. The standard HTTP Bot API caps at 50 MB.
- **4 GB uploads** (Telegram Premium) require a `SESSION_STRING` of a premium account.
- **YouTube downloads** use a format-list retry strategy — tries H.264/AAC first, falls back through progressively looser formats, never fails with "format not available".
- **Dynamic quality selector** — buttons are generated from the actual available resolutions. If 1080p isn't available for a video, it won't show up as an option.
- **Audio-only sources** (SoundCloud, Bandcamp, etc.) automatically show **Best Audio** and **MP3** buttons instead of video resolutions.
- **MP3 extraction** uses ffmpeg's `FFmpegExtractAudio` postprocessor at 192 kbps.
- **HLS/DASH streams** (`.m3u8`, `.mpd`) are downloaded via `ffmpeg -c copy` and remuxed to `.mp4`.
- Files are downloaded to `./DOWNLOADS/` and deleted immediately after upload.
- Thumbnails are stored as Telegram `file_id` strings in MongoDB — no local files needed.
