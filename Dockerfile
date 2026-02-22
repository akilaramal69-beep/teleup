FROM python:3.11-slim

# Install system dependencies + Node.js 20 (for bgutil POT server)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg git gcc python3-dev curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── bgutil PO Token provider ──────────────────────────────────────────────────
# Clones the bgutil server and installs deps; builds the TypeScript source.
# The yt-dlp plugin is installed via pip and auto-discovered by yt-dlp.
RUN git clone --depth 1 --single-branch --branch 1.2.2 \
    https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /opt/bgutil && \
    cd /opt/bgutil/server && npm ci && npx tsc
# pip plugin — yt-dlp picks this up automatically, no code changes needed
RUN pip install --no-cache-dir bgutil-ytdlp-pot-provider

# Copy project files
COPY . .

# Create downloads directory
RUN mkdir -p DOWNLOADS

EXPOSE 8080

# Start bgutil POT HTTP server (port 4416) in background, then start the bot
CMD node /opt/bgutil/server/build/main.js & python3 bot.py
