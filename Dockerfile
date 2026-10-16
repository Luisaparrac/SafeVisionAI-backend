# Local and CI image of the backend. The hosting platform does not use it: it
# installs requirements.txt and runs the start command of render.yaml directly.
# This image does the same, so what runs here is what runs in production.

# --- Build stage: production dependencies only, in a virtual environment ---
FROM python:3.12-slim AS build
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# --- Runtime stage: the environment and the source code, without build leftovers ---
FROM python:3.12-slim
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY src ./src
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ['PORT'] + '/health', timeout=2)"
# Same command as startCommand in render.yaml (a test keeps them equal).
CMD ["sh", "-c", "uvicorn safevision.adapters.inbound.http.app:app --app-dir src --host 0.0.0.0 --port $PORT"]
