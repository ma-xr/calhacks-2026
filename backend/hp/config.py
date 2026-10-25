"""Paths and secrets. Keys come from the project-root .env and are never logged."""
import os
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
WORLD_JSON = ROOT / "data" / "processed" / "world.json"
DATA_BACKEND = ROOT / "data" / "backend"
CACHE = ROOT / "data" / "cache"
RESEARCH_PARAMS = ROOT / "research" / "parameters" / "parameters.json"
VALIDATION_DIR = ROOT / "research" / "validation"

_env = {**dotenv_values(ROOT / ".env"), **{k: v for k, v in os.environ.items() if k.endswith(("_KEY", "_TOKEN", "_URL", "_ID"))}}


def secret(name: str):
    v = _env.get(name)
    return v or None


API_PORT = int(os.environ.get("HP_PORT", "8787"))
