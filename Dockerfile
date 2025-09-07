FROM python:3.10-slim

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl unzip xvfb x11-utils fonts-liberation \
    libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libcairo2 libcups2 libdbus-1-3 libdrm2 libegl1 \
    libgbm1 libglib2.0-0 libgtk-3-0 libnspr4 libnss3 \
    libpango-1.0-0 libpangocairo-1.0-0 libxcomposite1 \
    libxrandr2 libxkbcommon0 libx11-xcb1 libxss1 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Firefox only for you)
RUN playwright install --with-deps firefox

WORKDIR /app
CMD ["python", "--version"]
