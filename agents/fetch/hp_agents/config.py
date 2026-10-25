"""Paths, env and agent seeds. Keys come from the project-root .env and are never logged."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

FETCH_DIR = Path(__file__).resolve().parent.parent          # agents/fetch
REPO_ROOT = FETCH_DIR.parent.parent
load_dotenv(REPO_ROOT / ".env")
load_dotenv(FETCH_DIR / ".env")                             # optional local overrides

SIM_API = os.getenv("HP_SIM_API", "http://localhost:8787").rstrip("/")
WORLD_JSON = Path(os.getenv("HP_WORLD_JSON", REPO_ROOT / "data" / "processed" / "world.json"))
ASI_ONE_API_KEY = os.getenv("ASI_ONE_API_KEY") or os.getenv("ASI1_API_KEY")
ASI_ONE_URL = os.getenv("ASI_ONE_URL", "https://api.asi1.ai/v1/chat/completions")
ASI_ONE_MODEL = os.getenv("ASI_ONE_MODEL", "asi1-mini")
AGENTVERSE_API_KEY = os.getenv("AGENTVERSE_API_KEY")
# Optional public link to the 3D replay; "{id}" is replaced with the scenario id.
REPLAY_URL = os.getenv("HP_REPLAY_URL", "")
# Payment tier for the hearing brief (Agent Payment Protocol).
BRIEF_PRICE_FET = os.getenv("HP_BRIEF_PRICE_FET", "2")
BRIEF_CURRENCY = os.getenv("HP_BRIEF_CURRENCY", "FET")


def seed(role: str) -> str:
    """Stable per-role seed. Addresses derive from it, so it lives in a gitignored file."""
    env = os.getenv(f"HP_SEED_{role.upper()}")
    if env:
        return env
    path = FETCH_DIR / ".seeds" / role
    if not path.exists():
        path.parent.mkdir(exist_ok=True)
        path.write_text(secrets.token_hex(32))
        path.chmod(0o600)
    return path.read_text().strip()
