# Central de Mini Novelas (TikTok)

Pipeline completo: **bíblia da série → retratos dos personagens → clipes com IA → edição → episódio pronto para postar** (vídeo + capa + texto do post).

- **Vídeo:** Gemini Omni Flash (`gemini-omni-1.2-flash`), substituto oficial do Veo 3.1 na Gemini API (o Veo 3.1 Preview foi desligado em 22/10/2026). Gera clipes de 3–15 s com áudio e falas, em 9:16, e mantém os personagens consistentes com até 6 imagens de referência.
- **Retratos:** Nano Banana 2.1 (`gemini-nano-banana-2.1`).
- **Edição:** ffmpeg. Gera 1080x1920 a 30 fps, com legendas grandes, gancho nos 3 primeiros segundos, etiqueta "SÉRIE · EP N", cartela "PARTE N+1" no final e áudio normalizado para o TikTok.

## Custo (preço oficial, nov/2026)

| Resolução | US$/segundo | Episódio de ~55 s |
|---|---|---|
| 720p (padrão; o editor sobe para 1080x1920) | ~0,07 | ~US$ 3,75 |
| 1080p | ~0,10 | ~US$ 5,60 |

Cada clipe gerado fica salvo e **nunca é refeito sem `--refazer`**. `gerar` recusa rodadas acima de `--orcamento` (padrão US$ 10).

## Uso

```bash
pip install pyyaml          # e ffmpeg instalado
export GEMINI_API_KEY=...   # chave do Google AI Studio (plano pago)

python central.py status      heranca-monteiro
python central.py personagens heranca-monteiro      # 2 retratos por personagem (1x por série)
python central.py custo       heranca-monteiro 1
python central.py prompt      heranca-monteiro 1 c3  # ver o prompt sem gastar nada
python central.py episodio    heranca-monteiro 1      # gera as cenas + edita
python central.py gerar       heranca-monteiro 1 --refazer c3   # refaz só uma cena ruim
python central.py editar      heranca-monteiro 1 --sem-legenda
```

Saída em `saida/<serie>/`:
- `epNN.mp4`: episódio pronto
- `epNN_capa.jpg`: capa
- `epNN_post.txt`: legenda e hashtags

## Estrutura

```
series/<slug>/
  biblia.yaml        personagens (visual fixo), cenários, estilo
  temporada.md       arco dos 10 episódios e ganchos
  episodios/epNN.yaml  cenas: duração, cenário, refs (≤2 personagens), ação, falas com tempo
  personagens/       retratos de referência gerados (versionados: são a "cara" da série)
estudio/             gemini.py (API), serie.py (prompts), editor.py (ffmpeg)
```

### Regras para escrever cenas
- De 3 a 15 s por cena; o ideal é de 9 a 12 s.
- No máximo **2 personagens com `refs`** por cena (limite do modelo). Outros personagens entram em `figurantes`, de preferência ao fundo ou fora de foco.
- Falas curtas (até ~8 palavras), cada uma com o tempo `t` em segundos. Esse tempo também posiciona a legenda.
- Toda cena termina numa reação, e o episódio termina num gancho.
