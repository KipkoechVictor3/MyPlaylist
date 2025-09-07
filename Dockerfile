# Start from a base image that already has Python
FROM python:3.10-slim

# Install system dependencies for Playwright's Firefox browser
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libegl1 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libxcomposite1 \
    libxrandr2 \
    libxkbcommon0 \
    libx11-xcb1 \
    libxss1 \
    libxshmfence1 \
    libxvidcore4 \
    --fix-missing \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install playwright aiohttp httpx playwright-stealth requests

# Install Playwright browsers (Firefox)
RUN playwright install firefox
