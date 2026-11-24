# PLANO DE AÇÃO — ClipForge (clone do SmartClips, grátis e local)

> Como usar: crie uma pasta `clipforge/`, salve este arquivo nela como `PLANO.md`, abra o Claude Code nessa pasta e peça: **"Leia o PLANO.md e execute a Fase 0. Quando terminar, rode os critérios de aceite e me mostre o resultado antes de ir para a próxima fase."** Repita fase por fase.

---

## 1. Objetivo

App que roda **100% no PC do Gabriel (Windows)** e transforma vídeos longos (lives, podcasts, tutoriais, demos de produto) em cortes verticais 9:16 com legenda animada, prontos para o TikTok, em **fluxo contínuo** (joga o vídeo numa pasta → saem os cortes + fila de postagem).

Referência visual/funcional: SmartClips (screenshot enviado): partes de 15 min selecionáveis, presets de duração, proporção 9:16/1:1/original, quantidade de cortes, botão "Obter clipes em 1 clique", barra de progresso, biblioteca.

**Princípios:** grátis primeiro, offline por padrão, nunca depende de um serviço pago, tudo retomável (cache), sempre com plano B se uma peça falhar.

**Hardware alvo:** Ryzen 5 3600X, GTX 970, 16 GB RAM, Windows. Consequência: transcrição em **CPU (int8)**; não depender de CUDA.

---

## 2. Regras de monetização (guardrails do produto)

| Fato | Impacto no projeto |
|---|---|
| Creator Rewards exige 10 mil seguidores, 100 mil views em 30 dias, vídeos originais com mais de 1 minuto; Brasil está entre os países elegíveis | Criar preset **"Rewards" (62–110 s)** |
| TikTok não paga conteúdo reaproveitado de terceiros ("copiado integralmente" ou com mudanças leves) | App é para **conteúdo do próprio usuário** (lives, podcast, aulas, vídeos de produto Shopee/afiliado) ou com licença/permissão. Deixar isso no README e na tela inicial |
| Vídeo curto (<1 min) não entra no Rewards, mas serve para crescer seguidores e para afiliado (Shopee / TikTok Shop) | Presets "Curtos" e "Auto" continuam existindo |
| API de postagem do TikTok: app não auditado só publica em modo **privado** (auditoria leva dias a semanas); modo "Upload" (rascunho na caixa de entrada) não é claro na documentação sem auditoria | **Não** automatizar postagem na v1. Gerar **fila de postagem** (CSV + legenda .txt + horários) e agendar no TikTok Studio. API vira fase opcional |

---

## 3. Stack (tudo gratuito)

| Etapa | Ferramenta | Observação |
|---|---|---|
| Linguagem | Python 3.11+ | stdlib sempre que possível |
| Áudio/vídeo | **FFmpeg + FFprobe** (`winget install Gyan.FFmpeg`) | build "full" inclui libass (legendas) |
| Transcrição | **faster-whisper**, modelo `small`, `device=cpu`, `compute_type=int8`, `word_timestamps=True`, `vad_filter=True`, `beam_size=1` | benchmark de referência: modelo small int8 em CPU transcreve ~13 min de áudio em ~2 min; vídeo de 10 h = só as partes escolhidas |
| Achar momentos | 3 modos: **(a) Gemini free tier** via REST/urllib, **(b) Ollama local**, **(c) heurística offline** (sem IA) | (c) é o plano B sempre; qualquer erro de LLM cai nele automaticamente |
| Rosto → recorte 9:16 | **OpenCV `opencv-python-headless<5`** + Haar cascade | **Atenção:** testei e o OpenCV 5.x NÃO traz os arquivos Haar; fixar `<5` no requirements |
| Legendas | arquivo **ASS** gerado em Python, queimado com filtro `ass` do FFmpeg | uma linha por palavra, palavra ativa destacada (estilo TikTok) |
| Interface | servidor local `http.server` (stdlib) + 1 HTML, só em `127.0.0.1`, com token | sem Flask/Electron |
| Automação contínua | loop de pasta monitorada + estado em JSON | roda como `vigiar_pasta.bat` |
| Empacotar | `.bat` de instalar/abrir; PyInstaller opcional no fim | |

**Pontos a verificar na hora (mudam rápido):**
- IDs de modelo Gemini: conferir no Google AI Studio. Vistos na pesquisa como gratuitos: `gemini-3.6-flash` e `gemini-3.1-flash-lite`. Modelos 2.5 foram desligados em 16/10/2026. Deixar lista de modelos em `config.json`, não no código.
- Gemini free tier pode usar os dados para melhorar produtos do Google: modo privado = Ollama ou heurística.
- Modelo do Ollama (`qwen2.5:7b` é só sugestão; com 16 GB RAM e sem GPU boa, usar modelo ≤7B quantizado) → configurável.

---

## 4. Arquitetura e pastas

```
clipforge/
├─ PLANO.md
├─ CLAUDE.md              # contexto fixo p/ o Claude Code (ver seção 9)
├─ README.md
├─ requirements.txt       # faster-whisper, opencv-python-headless<5, numpy
├─ config.json            # padrões; config.local.json (chaves) fica no .gitignore
├─ clipforge.py           # CLI: doctor | run | watch | ui
├─ engine/
│  ├─ config.py           # carrega/mescla config
│  ├─ media.py            # ffprobe/ffmpeg, extração de áudio, rotação
│  ├─ transcribe.py       # faster-whisper + cache por parte
│  ├─ llm.py              # gemini / ollama / none (JSON robusto)
│  ├─ moments.py          # heurística + LLM + snap em fronteira de frase + seleção
│  ├─ reframe.py          # rastreio de rosto + expressão de crop suave
│  ├─ captions.py         # gerador de ASS (legenda + título gancho)
│  ├─ render.py           # ffmpeg: crop/blur + ass + loudnorm + thumb
│  ├─ pipeline.py         # orquestra tudo, callbacks de progresso/cancelar
│  └─ watcher.py          # pasta monitorada
├─ ui/  server.py + index.html
├─ entrada/  (vídeos novos)   entrada/_feito/   entrada/_erro/
├─ saida/<video>/  clip_01.mp4, clip_01.txt, thumb, manifest.json
├─ saida/fila_postagem.csv
└─ tests/  (vídeos sintéticos, transcrição falsa, testes automáticos)
```

**Fluxo de dados:** vídeo → partes de 15 min → áudio 16 kHz por parte → transcrição com palavras (cache) → candidatos (LLM ou heurística) → ranking global, sem sobreposição → para cada corte: rastreio de rosto → ASS → render → manifest + fila.

---

## 5. Fases

Cada fase termina com **critérios de aceite** que o Claude Code deve executar e mostrar. Não avançar sem passar.

### Fase 0 — Base e diagnóstico
**Fazer:** estrutura de pastas, `requirements.txt` (com `opencv-python-headless<5`), `config.json`, `.gitignore`, `clipforge.py doctor`.
`doctor` checa: Python, ffmpeg/ffprobe no PATH, filtro `ass` presente, `faster_whisper` e `cv2` importáveis, arquivo Haar existente, chave Gemini (sem imprimir), Ollama acessível, modelo Whisper já baixado.
**Aceite:** `python clipforge.py doctor` imprime ✔/✘ por item com a instrução de correção de cada ✘ (ex.: `winget install Gyan.FFmpeg`).

### Fase 1 — Mídia, partes e transcrição
**Fazer:** `media.probe` (duração, fps, resolução, rotação de celular), `make_parts` (partes de N min numeradas como no SmartClips: Parte 20 = 4:45:00–5:00:00), extração de áudio por parte, `transcribe_range` com **cache em disco por (arquivo, modelo, idioma, intervalo)**, progresso e cancelamento.
**Aceite:** transcrever 3 min de vídeo real em PT-BR gera JSON com palavras e tempos; segunda execução usa o cache (instantânea); reportar tempo vs. duração (meta: ≥3× tempo real na CPU com `small`).

### Fase 2 — Escolher os melhores momentos
**Fazer:**
1. Frases a partir das palavras (pontuação + pausas >0,8 s + limite de 30 palavras).
2. **Heurística:** janelas que começam/terminam em fronteira de frase dentro de [min, max]; nota por densidade de fala, pergunta/gancho no início, números, palavras de ênfase PT/EN, pausas (penalidade), começo fraco (penalidade). Seleção gananciosa sem sobreposição.
3. **LLM:** prompt pedindo JSON `{"clips":[{start,end,title,hashtags,score,reason}]}` com transcrição `[ini-fim] texto`; parser tolerante (remove cercas ```), retry em 429 com espera, lista de modelos de fallback; depois **snap** de start/end para a fronteira de frase mais próxima (±4 s) e validação de duração.
4. Qualquer falha de LLM → cai na heurística e registra no log.
5. Gerar título, descrição e hashtags (LLM, ou 1ª frase + palavras-chave na heurística).
**Aceite:** com transcrição de teste, retorna N cortes dentro de [min, max], sem sobreposição, começando e terminando em frase completa; teste com resposta de LLM simulada (JSON sujo, tempos fora da fronteira, duração inválida) passa; sem chave de API o modo heurístico funciona.

### Fase 3 — Reenquadramento, legenda e render
**Fazer:**
- `reframe.track_faces`: amostra 1 quadro/s, rosto maior com bônus de continuidade, preenche falhas, zona morta + suavização.
- Posição do crop como **expressão linear por partes** do `t` no filtro `crop` do FFmpeg (soma de termos `max(0,t-ti)`, entre aspas simples), sem processar quadro a quadro.
- Layouts: `track` (rosto), `blur` (vídeo inteiro com fundo desfocado, ótimo p/ tela/gameplay/produto), `center`. Proporções 9:16 (1080×1920), 1:1, original.
- `captions.py`: ASS com 3 palavras por bloco, MAIÚSCULAS, palavra ativa em amarelo e maior, contorno preto, posição acima da zona de interface do TikTok (~30% da base); título gancho opcional nos 3 primeiros segundos no topo.
- `render.py`: `-ss/-t` antes do `-i`, `libx264 -preset veryfast -crf 20`, `loudnorm`, `+faststart`, thumbnail; opção `h264_nvenc` com fallback automático para x264. Rodar o ffmpeg com `cwd` na pasta do corte e `ass=arquivo.ass` relativo (evita problema de `C:\` no filtro).
**Aceite:** gerar 3 cortes de vídeo de teste (com e sem rosto) e abrir 1 frame de cada: legenda legível e centralizada, rosto dentro do enquadramento, áudio sincronizado; arquivo final 1080×1920, H.264/AAC.

### Fase 4 — Pipeline completo + fila de postagem
**Fazer:** `pipeline.process(video, opts, progress, cancel)`; `Options` (min/max, quantidade ou automático até 30, proporção, layout, legendas, título, partes escolhidas, modelo, idioma, LLM, encoder); presets **Auto 20–60 s, Curtos 15–30, Longos 45–90, Rewards 62–110, Personalizado**; `manifest.json` por vídeo; `.txt` por corte (descrição + hashtags prontas p/ colar); `saida/fila_postagem.csv` com horário sugerido (padrão 12:00, 18:30, 21:00, continuando de onde parou).
**Aceite:** `python clipforge.py run video.mp4 --preset rewards --count 5 --parts 2-4` gera os cortes, manifest e CSV; interromper no meio e rodar de novo **retoma** sem retranscrever.

### Fase 5 — Fluxo contínuo
**Fazer:** `clipforge.py watch entrada/`: detecta arquivo novo e estável (tamanho igual em 2 varreduras), processa, move para `_feito/`; erro → `_erro/` + `.erro.txt` com o motivo; log em arquivo; fila sequencial (1 vídeo por vez); `vigiar_pasta.bat`; opção de **agendar com o Agendador de Tarefas do Windows** (instruções no README).
**Aceite:** copiar 2 vídeos para `entrada/` com o watcher rodando → ambos processados em ordem, arquivos movidos, CSV atualizado; um arquivo corrompido vai para `_erro/` sem derrubar o loop.

### Fase 6 — Interface local estilo SmartClips
**Fazer:** `clipforge.py ui` abre `http://127.0.0.1:8765`. Segurança: só 127.0.0.1, validar header `Host`, token aleatório por sessão nas chamadas da API. Telas: **Novos cortes** (escolher arquivo com diálogo nativo `tkinter`, chips de partes clicáveis, presets de duração, proporção, enquadramento, slider de quantidade + Automático, toggles de legenda e título, botão "Obter clipes em 1 clique", barra de progresso, cancelar), **Biblioteca** (cards com preview `<video>` com suporte a Range, nota, título, botões copiar legenda/abrir pasta), **Pasta monitorada** (liga/desliga o watcher). Visual: escuro com gradiente azul→rosa como no screenshot.
**Aceite:** processar um vídeo inteiro pela interface; cancelar funciona; reabrir a UI mostra a biblioteca; chamada à API sem token retorna 403.

### Fase 7 — Polimento e extras (por ordem de valor)
1. **Remover silêncios** dentro do corte (aba "Tirar silêncios" do SmartClips) usando lacunas entre palavras.
2. **Pasta de intro/outro e marca** (logo, CTA "link na bio" / cupom Shopee) aplicada no final do corte.
3. **Detecção de quem fala** (alternar rosto em podcast com 2 pessoas) por energia de áudio por canal ou diarização.
4. **Pós-edição manual:** ajustar início/fim de um corte na UI e re-renderizar.
5. **Postagem via API do TikTok** (só depois de registrar app + auditoria, e só para contas do próprio dono) ou integração com ferramenta de agendamento.
6. Empacotar com PyInstaller; atualizador simples.

---

## 6. Estratégia de testes (para o Claude Code seguir)

- `tests/make_samples.py` cria vídeos sintéticos com FFmpeg (padrão de teste + tom) e usa `skimage.data.astronaut()` para um vídeo com rosto se movendo (testa o rastreio sem baixar nada).
- **Transcrição falsa** em JSON (`--transcript arquivo.json`) para testar fases 2–6 sem depender do Whisper.
- Teste real de transcrição somente na máquina do Gabriel (modelos vêm do Hugging Face).
- Verificações automáticas com `ffprobe`: resolução, codec, duração dentro de [min, max].
- Conferir **visualmente** 1 frame por corte (legenda, rosto) antes de dar a fase por concluída.

---

## 7. Riscos e decisões em aberto

| Risco | Mitigação |
|---|---|
| Transcrição lenta em vídeos de 10 h | Processar só as partes escolhidas; cache; modelo `base` como modo rápido |
| Haar erra rosto (óculos, perfil, luz fraca) | Fallback para centro; `blur` como layout alternativo |
| Heurística gera cortes medianos | Gemini free ou Ollama; botão para regenerar com outro modo |
| Limites do Gemini free (por minuto/dia) | Retry com espera, fallback de modelo, depois heurística |
| TikTok marcar conteúdo como não original | Usar só conteúdo próprio/licenciado; adicionar título/legenda/CTA próprios; README com aviso |
| Fonte da legenda não existir | Configurável (`Arial Black`/`Impact` no Windows) |

**Decisões do Gabriel antes da Fase 2:**
1. Qual conteúdo será a fonte principal (suas lives, podcast, vídeos de produto Shopee)? Define os presets e o tom das hashtags.
2. Idioma principal (PT-BR fixo acelera e melhora a transcrição).
3. Vai usar Gemini (precisa de chave grátis no AI Studio) ou prefere 100% offline?

---

## 8. Primeiros prompts prontos para o Claude Code

**Prompt 1 (Fase 0):**
> Leia o PLANO.md. Execute a Fase 0 por completo: crie a estrutura de pastas, requirements.txt (com opencv-python-headless<5), config.json, .gitignore e o comando `doctor`. Rode `python clipforge.py doctor` e me mostre a saída. Não avance para a Fase 1.

**Prompt 2 (Fases 1–2):**
> Execute as Fases 1 e 2 do PLANO.md. Crie os testes com transcrição falsa e rode todos. Mostre os critérios de aceite cumpridos um a um.

**Prompt 3 (Fases 3–4):**
> Execute as Fases 3 e 4. Gere vídeos de teste sintéticos (incluindo um com rosto em movimento usando skimage astronaut), renderize 3 cortes e me mostre 1 frame de cada para eu conferir.

**Prompt 4 (Fases 5–6):**
> Execute as Fases 5 e 6. Suba a UI, processe um vídeo pela API e confirme o 403 sem token.

---

## 9. CLAUDE.md (copiar para a raiz do projeto)

```
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
```

---

## Fontes consultadas
- TikTok Creator Rewards (requisitos 2026): https://www.toptal.com/creator/post/how-to-join-the-tiktok-creator-rewards-program · https://metricool.com/tiktok-creator-fund/ · https://findclout.com/blog/tiktok-creator-rewards-reposted-clips
- Regras de originalidade: https://www.tiktok.com/community-guidelines/en/integrity-authenticity/ · https://newsroom.tiktok.com/introducing-the-new-creator-rewards-program
- API de postagem do TikTok (auditoria, modo privado, limites): https://developers.tiktok.com/docs/en/content-posting-api-get-started · https://www.socialync.io/blog/tiktok-content-posting-api-guide-2026
- faster-whisper (benchmarks, palavras com tempo): https://github.com/SYSTRAN/faster-whisper
- Gemini free tier (2026): https://apidog.com/blog/gemini-api-free-tier/
- Projetos open source de referência: https://github.com/mutonby/openshorts · https://github.com/ClipsAI/clipsai · https://github.com/aionixos/openclip
