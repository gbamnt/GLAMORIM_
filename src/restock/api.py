"""Classe exposta ao JS via pywebview js_api. Única porta de entrada da UI.

Regra (SPEC 7): todo método, exceto unlock/vault_status, exige o cofre desbloqueado.
Nenhum dado decifrado volta para a UI.
"""

from __future__ import annotations

import functools
from typing import Any, Callable

from restock import __version__
from restock.events import bus


class LockedError(Exception):
    pass


def requires_unlock(fn: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(fn)
    def wrapper(self: "Api", *args: Any, **kwargs: Any) -> Any:
        if not self.is_unlocked():
            return {"ok": False, "erro": "bloqueado"}
        return fn(self, *args, **kwargs)

    return wrapper


class Api:
    def __init__(self) -> None:
        self._unlocked = False  # substituído pelo vault/session na etapa A2

    # ---- sem exigência de desbloqueio ----
    def app_info(self) -> dict[str, Any]:
        return {"ok": True, "versao": __version__}

    def is_unlocked(self) -> bool:
        return self._unlocked

    # ---- exige desbloqueio ----
    @requires_unlock
    def poll_events(self) -> dict[str, Any]:
        return {"ok": True, "eventos": bus.drain()}
