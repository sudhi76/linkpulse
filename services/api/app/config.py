import os

# All configuration comes from environment variables, so the same image runs
# unchanged in Docker Compose, kind and EKS (12-factor style).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./linkpulse.db")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
CODE_LENGTH = int(os.getenv("CODE_LENGTH", "7"))
# Commit SHA the image was built from, set at build time (see Dockerfile).
# "dev" for local runs outside an image built by CI.
VERSION = os.getenv("APP_VERSION", "dev")
