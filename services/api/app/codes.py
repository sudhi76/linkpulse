import re
import secrets
import string

ALPHABET = string.ascii_letters + string.digits  # base62

# Custom aliases: letters, digits, "-" and "_", 3 to 32 characters.
ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")

# Paths the API itself uses; a short link must never shadow them.
RESERVED = {"links", "healthz", "readyz", "metrics", "docs", "redoc", "openapi.json"}


def generate_code(length: int) -> str:
    """Random base62 code. secrets (not random) makes codes unguessable."""
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def is_valid_alias(alias: str) -> bool:
    return bool(ALIAS_PATTERN.match(alias)) and alias.lower() not in RESERVED
