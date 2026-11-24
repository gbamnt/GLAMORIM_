"""Carrega config.json e mescla com config.local.json (chaves/ajustes pessoais, fora do git)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
ARQ_PADRAO = RAIZ / "config.json"
ARQ_LOCAL = RAIZ / "config.local.json"


def mesclar(base: dict, extra: dict) -> dict:
    """Mescla recursiva: valores de `extra` sobrescrevem `base` (dicts são mesclados)."""
    saida = dict(base)
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(saida.get(k), dict):
            saida[k] = mesclar(saida[k], v)
        else:
            saida[k] = v
    return saida


def _ler_json(caminho: Path) -> dict:
    if not caminho.exists():
        return {}
    with caminho.open(encoding="utf-8") as f:
        return json.load(f)


def carregar(padrao: Path = ARQ_PADRAO, local: Path = ARQ_LOCAL) -> dict[str, Any]:
    return mesclar(_ler_json(padrao), _ler_json(local))


def chave_gemini(cfg: dict | None = None) -> str | None:
    """Chave do Gemini: variável de ambiente GEMINI_API_KEY ou config.local.json -> llm.gemini.chave.
    Nunca imprimir o valor retornado."""
    env = os.environ.get("GEMINI_API_KEY", "").strip()
    if env:
        return env
    cfg = cfg if cfg is not None else carregar()
    chave = str(cfg.get("llm", {}).get("gemini", {}).get("chave", "") or "").strip()
    return chave or None


def pasta(cfg: dict, nome: str) -> Path:
    """Resolve uma pasta de `pastas` relativa à raiz do projeto."""
    p = Path(cfg["pastas"][nome])
    return p if p.is_absolute() else RAIZ / p
