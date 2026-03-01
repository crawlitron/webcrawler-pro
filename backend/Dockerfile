FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers as root before switching user
# Install Playwright browser (Debian-based image - libasound2 is available)
# Using || true as fallback since CWV is optional feature
RUN playwright install chromium 2>/dev/null || true && \
    playwright install-deps chromium 2>/dev/null || true

COPY . .

# Set ownership
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
