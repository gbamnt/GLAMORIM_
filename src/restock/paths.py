"""Pasta de dados do app (fora do projeto, permissão só do usuário do SO)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "RestockApp"


def data_dir() -> Path:
    """Retorna (e cria) a pasta de dados do app.

    - Windows: %LOCALAPPDATA%\\RestockApp
    - macOS:   ~/Library/Application Support/RestockApp
    - Linux:   $XDG_DATA_HOME/RestockApp (ou ~/.local/share/RestockApp) — só para dev/testes
    A variável RESTOCK_DATA_DIR sobrescreve (usada pelos testes).
    """
    override = os.environ.get("RESTOCK_DATA_DIR")
    if override:
        base = Path(override)
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_DIR_NAME
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_DIR_NAME

    _ensure_private_dir(base)
    for sub in ("profiles", "screenshots", "logs"):
        _ensure_private_dir(base / sub)
    return base


def _ensure_private_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        # rwx só para o dono. No Windows, %LOCALAPPDATA% já é restrito ao usuário.
        os.chmod(p, 0o700)


def db_path() -> Path:
    return data_dir() / "restock.db"


def profiles_dir() -> Path:
    return data_dir() / "profiles"


def screenshots_dir() -> Path:
    return data_dir() / "screenshots"


def logs_dir() -> Path:
    return data_dir() / "logs"


def selectors_override_path() -> Path:
    return data_dir() / "selectors.override.yaml"


def resource_path(rel: str) -> Path:
    """Caminho de recurso empacotado (ui/, selectors.yaml), compatível com PyInstaller."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base / rel
