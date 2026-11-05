"""Entrypoint: abre a janela pywebview. Nenhuma porta de rede é aberta (sem servidor HTTP)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import webview  # noqa: E402

from restock import paths  # noqa: E402
from restock.api import Api  # noqa: E402
from restock.db.repo import init_db  # noqa: E402


def main() -> None:
    paths.data_dir()
    init_db()
    api = Api()
    index = paths.resource_path("ui/index.html")
    webview.create_window(
        "Restock",
        url=index.as_uri(),  # file:// — sem servidor HTTP local
        js_api=api,
        width=1200,
        height=800,
        min_size=(960, 640),
    )
    # http_server=False garante que o pywebview não sobe servidor local.
    webview.start(http_server=False, private_mode=True)


if __name__ == "__main__":
    main()
