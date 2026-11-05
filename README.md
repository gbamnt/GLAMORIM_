# Restock (amazon.com.br)

App desktop pessoal de monitoramento e compra. Especificação completa em [`SPEC.md`](SPEC.md).

## Status

| Etapa | Situação |
|---|---|
| A1 — Scaffold, dependências com hash, pasta de dados, SQLite | ✅ |
| A2 — Cofre + desbloqueio | ⏳ |

## Instalação (Windows / macOS)

Requer Python 3.12.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS: source .venv/bin/activate
pip install --require-hashes -r requirements.txt
python -m playwright install chromium
python app.py
```

Testes: `python -m pytest -q`

## Desenvolvimento

- Atualizar dependências: edite `requirements.in` e rode
  `uv pip compile requirements.in --universal --generate-hashes --python-version 3.12 -o requirements.txt`.
- CSS (Tailwind, build local, sem CDN):
  `npx tailwindcss@3.4.17 -c tailwind.config.js -i ui/input.css -o ui/styles.css --minify`.
  O `ui/styles.css` gerado é versionado, então rodar o app não exige Node.

## Pasta de dados

- Windows: `%LOCALAPPDATA%\RestockApp\`
- macOS: `~/Library/Application Support/RestockApp/`

Contém `restock.db`, `profiles/`, `screenshots/`, `logs/` e `selectors.override.yaml`. Nunca é versionada.
