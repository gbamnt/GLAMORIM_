"""ClipForge — corta vídeos longos em clipes verticais com legenda, 100% local.

Uso:
    python clipforge.py doctor
    python clipforge.py run VIDEO [opções]     (Fase 4)
    python clipforge.py watch [PASTA]          (Fase 5)
    python clipforge.py ui                     (Fase 6)
"""
from __future__ import annotations

import argparse
import sys


def _utf8_console() -> None:
    # Console do Windows (cp1252) não imprime ✔/✘ por padrão.
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass


def main(argv: list[str] | None = None) -> int:
    _utf8_console()
    ap = argparse.ArgumentParser(prog="clipforge", description="Cortes 9:16 com legenda, 100% local.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="verifica dependências e configuração")
    sub.add_parser("run", help="processa um vídeo (Fase 4)")
    sub.add_parser("watch", help="pasta monitorada (Fase 5)")
    sub.add_parser("ui", help="interface local (Fase 6)")
    args, _resto = ap.parse_known_args(argv)

    if args.cmd == "doctor":
        from engine import doctor
        return doctor.executar()
    fases = {"run": 4, "watch": 5, "ui": 6}
    print(f"'{args.cmd}' ainda não implementado (chega na Fase {fases[args.cmd]}).")
    return 2


if __name__ == "__main__":
    sys.exit(main())
