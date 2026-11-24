# ClipForge
App local (Windows) que corta vídeos longos em clipes 9:16 com legenda para TikTok.
Regras:
- Tudo grátis e offline por padrão. LLM é opcional; sempre ter fallback heurístico.
- Hardware alvo: CPU Ryzen 5 3600X, 16 GB RAM, GTX 970. Whisper em CPU int8.
- Preferir stdlib. Dependências: faster-whisper, opencv-python-headless<5, numpy.
- Nunca imprimir/commitar chaves de API. Chaves só em config.local.json ou variável de ambiente.
- Tudo deve ser retomável (cache por parte) e cancelável.
- Caminhos Windows: usar pathlib; rodar ffmpeg com cwd e nomes relativos para filtros.
- Ao final de cada fase: rodar os testes, mostrar evidências (saída de comando, frame) e esperar aprovação.
- Texto da interface e README em português do Brasil.
