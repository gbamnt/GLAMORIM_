# ClipForge

Transforma vídeos longos (lives, podcasts, aulas, demos de produto) em cortes verticais 9:16 com legenda animada para o TikTok. Roda **100% no seu PC**, de graça e offline por padrão. Plano completo em [`PLANO.md`](PLANO.md).

> ⚠️ **Use só conteúdo seu ou licenciado.** O TikTok não paga (Creator Rewards) por conteúdo reaproveitado de terceiros, nem quando a mudança é pequena. O ClipForge foi feito para cortar as **suas** lives, podcasts, aulas e vídeos de produto.

## Status

| Fase | Situação |
|---|---|
| 0 — Base e diagnóstico (`doctor`) | ✅ |
| 1 — Mídia, partes e transcrição | ⏳ |
| 2 — Melhores momentos | ⏳ |
| 3 — Reenquadramento, legenda, render | ⏳ |
| 4 — Pipeline + fila de postagem | ⏳ |
| 5 — Pasta monitorada | ⏳ |
| 6 — Interface local | ⏳ |

## Instalação (Windows)

1. Instale o Python 3.11+ e o FFmpeg:
   ```
   winget install Python.Python.3.12
   winget install Gyan.FFmpeg
   ```
   Feche e reabra o terminal.
2. Dê dois cliques em `instalar.bat` (cria o `.venv` e instala as dependências).
3. Confira se está tudo certo:
   ```
   .venv\Scripts\python clipforge.py doctor
   ```

## Configuração

- `config.json`: padrões (modelo Whisper, presets, horários da fila etc.).
- `config.local.json`: **seus** ajustes e chaves. Não vai para o git. Exemplo:
  ```json
  {"llm": {"modo": "gemini", "gemini": {"chave": "SUA_CHAVE"}}}
  ```
  A chave também pode vir da variável de ambiente `GEMINI_API_KEY`.
- Modos de IA para achar os momentos: `heuristica` (offline, padrão), `gemini` (free tier; o Google pode usar os dados) ou `ollama` (local e privado).

## Testes

```
.venv\Scripts\python -m unittest discover -s tests -t .
```
