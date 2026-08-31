from __future__ import annotations

from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

try:
    from dotenv import load_dotenv
except ImportError:
    pass
else:
    load_dotenv(_ENV_FILE)
