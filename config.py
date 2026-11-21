"""Configuração compartilhada pela interface e pelos scripts."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=False)


def setting(name: str, default: str = "") -> str:
    value = os.getenv(name, default).strip()
    if not value:
        raise ValueError(f"Configure {name} no arquivo .env.")
    return value


def timeout_seconds() -> float:
    value = float(setting("DB_TIMEOUT_SECONDS", "5"))
    if not 0 < value <= 60:
        raise ValueError("DB_TIMEOUT_SECONDS deve estar entre 0 e 60 segundos.")
    return value
