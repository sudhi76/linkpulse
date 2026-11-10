# syntax=docker/dockerfile:1

# ---- Stage 1: build ---------------------------------------------------------
# Installs dependencies into a virtualenv. Build tools and pip caches stay in
# this stage and never reach the final image.
FROM python:3.13-slim AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only the requirements first: this layer is cached and reused until
# requirements.txt changes, so code edits don't reinstall every dependency.
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---- Stage 2: runtime -------------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Run as an unprivileged user with a fixed UID, so Kubernetes
# (runAsNonRoot) and policy engines can verify it.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home app

WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY app ./app

USER 10001
EXPOSE 8000

# Used by Docker and Compose. Kubernetes ignores it and uses its own probes.
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]

# Exec form (JSON array): uvicorn runs as PID 1 and receives SIGTERM directly,
# so pods shut down gracefully instead of being killed after the grace period.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
