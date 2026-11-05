"""Acesso ao SQLite. Conexões curtas, thread-safe por uso (uma conexão por chamada/thread)."""

from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from restock import paths
from restock.db.models import SCHEMA, SCHEMA_VERSION

_init_lock = threading.Lock()
_initialized: set[str] = set()


def _connect(db_file: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_file, timeout=10, isolation_level=None)  # autocommit; transações explícitas
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA secure_delete = ON")  # sobrescreve páginas apagadas (dados cifrados excluídos)
    return conn


def init_db(db_file: Path | None = None) -> Path:
    db_file = Path(db_file or paths.db_path())
    with _init_lock:
        conn = _connect(db_file)
        try:
            conn.executescript(SCHEMA)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        finally:
            conn.close()
        if os.name == "posix":
            os.chmod(db_file, 0o600)
        _initialized.add(str(db_file))
    return db_file


@contextmanager
def connect(db_file: Path | None = None) -> Iterator[sqlite3.Connection]:
    db_file = Path(db_file or paths.db_path())
    if str(db_file) not in _initialized:
        init_db(db_file)
    conn = _connect(db_file)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(db_file: Path | None = None) -> Iterator[sqlite3.Connection]:
    with connect(db_file) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        else:
            conn.execute("COMMIT")


# ---- config -------------------------------------------------------------

def get_config(chave: str, default: str | None = None) -> str | None:
    with connect() as c:
        row = c.execute("SELECT valor FROM config WHERE chave = ?", (chave,)).fetchone()
    return row["valor"] if row else default


def set_config(chave: str, valor: str) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO config(chave, valor) VALUES(?, ?) "
            "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
            (chave, valor),
        )


# ---- lock de checkout (SPEC 5) -----------------------------------------

def acquire_checkout_lock(produto_id: str) -> bool:
    """Só um checkout por produto: muda monitorando -> em_checkout atomicamente."""
    with connect() as c:
        cur = c.execute(
            "UPDATE produtos SET status = 'em_checkout' WHERE id = ? AND status = 'monitorando'",
            (produto_id,),
        )
        return cur.rowcount == 1
