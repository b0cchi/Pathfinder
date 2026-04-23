FROM python:3.14-slim-trixie

ENV DEBIAN_FRONTEND=noninteractive
# ブラウザのインストール先を固定して権限トラブルを防ぐ
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 基本ツール + Playwrightの実行に必要なライブラリ群
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl \
       ca-certificates \
       gnupg \
       git \
       # Playwright(Chromium)の依存関係
       libnss3 \
       libatk1.0-0 \
       libatk-bridge2.0-0 \
       libcups2 \
       libdrm2 \
       libxkbcommon0 \
       libxcomposite1 \
       libxdamage1 \
       libxfixes3 \
       libxrandr2 \
       libgbm1 \
       libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Node.js 24 (LTS)
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Playwright本体とChromiumブラウザをビルド時にインストール
# これにより実行時に毎回ダウンロードする手間を省き、エラーを防ぐ
RUN npm install -g playwright@latest \
    && npx playwright install chrome --with-deps

# pip 最新化
RUN python -m pip install --upgrade pip

CMD ["bash"]