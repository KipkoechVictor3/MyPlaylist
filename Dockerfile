FROM mcr.microsoft.com/playwright/python:v1.47.0-noble

# Set working directory
WORKDIR /app

# Copy requirements first (so Docker layer cache works)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Preinstall Playwright browsers inside the image
RUN playwright install --with-deps firefox chromium

# Copy project files
COPY . .

# Default command (optional — workflow overrides anyway)
CMD ["python", "master_script.py"]
