"""Barramento de eventos motor -> UI. Fila thread-safe; eventos passam pela redação."""

from __future__ import annotations

import itertools
import queue
import time
from dataclasses import asdict, dataclass, field
from typing import Any

_MAX_QUEUE = 1000


@dataclass
class Event:
    tipo: str                       # ex.: status, check, voltou, pausado, comprado, log
    mensagem: str = ""
    produto_id: str | None = None
    conta_id: str | None = None
    dados: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)
    seq: int = 0


class EventBus:
    def __init__(self) -> None:
        self._q: queue.Queue[Event] = queue.Queue(maxsize=_MAX_QUEUE)
        self._seq = itertools.count(1)

    def emit(self, tipo: str, mensagem: str = "", **kw: Any) -> None:
        ev = Event(tipo=tipo, mensagem=_redact(mensagem), seq=next(self._seq), **kw)
        try:
            self._q.put_nowait(ev)
        except queue.Full:  # descarta o mais antigo; a UI nunca deve travar o motor
            try:
                self._q.get_nowait()
            except queue.Empty:
                pass
            self._q.put_nowait(ev)

    def drain(self, limit: int = 200) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        while len(out) < limit:
            try:
                out.append(asdict(self._q.get_nowait()))
            except queue.Empty:
                break
        return out


def _redact(text: str) -> str:
    try:
        from restock.security.redact import redact_text
    except ImportError:  # redact.py chega na etapa A3
        return text
    return redact_text(text)


bus = EventBus()
