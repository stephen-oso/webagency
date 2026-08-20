# Stage 1: builder — install dependencies via Poetry
FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.in-project true \
    && poetry install --only main --no-root --no-interaction --no-ansi

# Stage 2: runtime — minimal image
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install Node.js and Vercel CLI
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g vercel && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY . .

# Install Playwright browser (Chromium) and its system dependencies
RUN /app/.venv/bin/playwright install chromium \
    && /app/.venv/bin/playwright install-deps chromium

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
