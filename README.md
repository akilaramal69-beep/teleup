# 🤖 Telegram URL Uploader Bot

Upload files up to **2 GB** to Telegram directly from any direct download URL. Built with [Pyrogram](https://docs.pyrogram.org/) (MTProto) for large file support, deployable on **Koyeb** with one click.

---

## ✨ Features

| Feature | Details |
|---|---|
| 📤 URL Upload | Send any direct URL — bot downloads & uploads to Telegram |
| 🎬 Smart MIME routing | Auto-sends as video / audio / photo / document |
| 💾 Up to 2 GB | Uses Pyrogram MTProto (not the limited HTTP Bot API) |
| 📝 Custom captions | Per-user saved captions |
| 🖼️ Thumbnails | Set a custom thumbnail for uploads |
| 📢 Broadcast | Send messages to all users (admin) |
| 📊 /status | CPU, RAM, disk usage (admin) |
| 🚫 Ban / unban | User management (admin) |
| ☁️ Koyeb ready | Docker + Flask health server included |

---

## 🚀 Bot Commands

```
start        – Check if bot is alive 🔔
help         – Show all commands ❓
about        – Bot info ℹ️
upload <url> – Upload file from URL 📤
caption <txt>– Set custom upload caption 📝
showcaption  – View your caption
clearcaption – Clear your caption
setthumb     – Reply to photo to set thumbnail 🖼️
showthumb    – View current thumbnail
delthumb     – Delete thumbnail

--- Admin only ---
broadcast    – Broadcast to all users 📢
total        – Total registered users 👥
ban <id>     – Ban a user ⛔
unban <id>   – Unban a user ✅
status       – Bot resource usage 🚀
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

---

## 🐳 Local Setup

```bash
git clone https://github.com/YOUR_USERNAME/tg-url-uploader.git
cd tg-url-uploader

# Copy and edit config
cp .env.example .env
# Fill in your values in .env

pip install -r requirements.txt
python bot.py
```

---

## ☁️ Deploy to Koyeb

### Method 1 — Docker (recommended)

1. Fork this repo on GitHub
2. Go to [koyeb.com](https://www.koyeb.com) → **Create Service** → **Docker**
3. Set the Docker image to your GitHub Container Registry image OR use **GitHub** source and enable Docker build
4. Add all environment variables from the table above
5. Set **Port** to `8080` (health check at `/health`)
6. Deploy! ✅

### Method 2 — GitHub + Buildpack

1. Connect your GitHub repo to Koyeb
2. Build Command: `pip install -r requirements.txt`
3. Run Command: `python bot.py`
4. Port: `8080`
5. Add env vars → Deploy ✅

---

## 📁 Project Structure

```
tg-url-uploader/
├── bot.py                  # Entrypoint (Pyrogram + Flask thread)
├── app.py                  # Flask health server
├── requirements.txt
├── Dockerfile
├── .env.example
└── plugins/
    ├── config.py           # Config from env vars
    ├── commands.py         # User commands (/start, /upload, etc.)
    ├── admin.py            # Admin commands (/broadcast, /ban, etc.)
    └── helper/
        ├── upload.py       # Download + upload logic with progress
        └── database.py     # MongoDB async helper
```

---

## 📝 Notes

- **2 GB limit** is achieved via Pyrogram's MTProto API. The standard Telegram HTTP Bot API is limited to 50 MB.
- **4 GB uploads** (Telegram Premium) require a valid `SESSION_STRING` of a premium account.
- The bot downloads files to `./DOWNLOADS/` temporarily and deletes them after upload.
