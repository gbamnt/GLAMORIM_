"""Cliente mínimo da Interactions API do Gemini (só biblioteca padrão).

- Vídeo: Gemini Omni Flash (`gemini-omni-1.2-flash`). O Veo 3.1 Preview foi
  desligado na Gemini API em 22/10/2026; o Omni é o substituto oficial.
- Imagem: Nano Banana 2.1 (`gemini-nano-banana-2.1`) para os retratos de referência.

Chave: lida de GEMINI_API_KEY. Na nuvem do Claude Code a chave fica salva como
"network secret" do ambiente e o proxy a injeta no header x-goog-api-key; nesse
caso a variável pode ficar vazia e um valor provisório é enviado (o proxy troca).
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BASE = "https://generativelanguage.googleapis.com/v1beta"
MODELO_VIDEO = os.environ.get("NOVELAS_MODELO_VIDEO", "gemini-omni-1.2-flash")
MODELO_IMAGEM = os.environ.get("NOVELAS_MODELO_IMAGEM", "gemini-nano-banana-2.1")

# Preço oficial (página de pricing, nov/2026): tokens de saída de vídeo a US$ 12/1M.
# 720p = 5.792 tokens/s (~US$ 0,07/s); 1080p = 8.688 tokens/s (~US$ 0,104/s).
PRECO_POR_SEGUNDO = {"360p": 0.023, "720p": 0.0695, "1080p": 0.104, "4k": 0.209}


class GeminiErro(RuntimeError):
    pass


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    h = {
        "Content-Type": "application/json",
        "x-goog-api-key": os.environ.get("GEMINI_API_KEY") or "injetada-pelo-proxy",
    }
    if extra:
        h.update(extra)
    return h


def _req(method: str, url: str, body: dict | None = None, timeout: int = 900,
         extra_headers: dict[str, str] | None = None, raw: bool = False) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=_headers(extra_headers))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = r.read()
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode(errors="replace")[:2000]
        raise GeminiErro(f"HTTP {e.code} em {method} {url.split('?')[0]}: {detalhe}") from None
    return payload if raw else json.loads(payload)


def _com_retentativa(fn, tentativas: int = 3):
    """Repete só erros transitórios (429/5xx/rede). Erros 4xx de conteúdo não se repetem."""
    espera = 15
    for i in range(tentativas):
        try:
            return fn()
        except GeminiErro as e:
            msg = str(e)
            transitorio = any(f"HTTP {c}" in msg for c in (429, 500, 502, 503, 504))
            if not transitorio or i == tentativas - 1:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if i == tentativas - 1:
                raise
        time.sleep(espera)
        espera *= 2


def _midias(resp: dict, tipo: str) -> list[dict]:
    """Acha blocos de mídia (`type` == tipo) em qualquer lugar da resposta."""
    achados: list[dict] = []

    def andar(x: Any) -> None:
        if isinstance(x, dict):
            if x.get("type") == tipo and ("data" in x or "uri" in x):
                achados.append(x)
            for v in x.values():
                andar(v)
        elif isinstance(x, list):
            for v in x:
                andar(v)

    # Saídas do modelo primeiro (a entrada também tem imagens de referência).
    saidas = [s for s in resp.get("steps", []) if s.get("type") == "model_output"]
    andar(saidas or resp.get("output_video") or resp.get("output_image") or resp)
    if not achados and isinstance(resp.get(f"output_{tipo}"), dict):
        achados.append(resp[f"output_{tipo}"])
    return achados


def _baixar_uri(uri: str, destino: Path) -> None:
    if uri.startswith("files/") or "/files/" in uri and ":download" not in uri:
        file_id = uri.split("files/")[-1].split(":")[0].split("?")[0]
        for _ in range(120):  # até ~10 min
            st = _req("GET", f"{BASE}/files/{file_id}", timeout=60)
            if st.get("state") == "ACTIVE":
                break
            if st.get("state") == "FAILED":
                raise GeminiErro(f"Arquivo {file_id} falhou no processamento")
            time.sleep(5)
        uri = f"{BASE}/files/{file_id}:download?alt=media"
    destino.write_bytes(_req("GET", uri, timeout=600, raw=True))


def _salvar(midia: dict, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if midia.get("data"):
        destino.write_bytes(base64.b64decode(midia["data"]))
    else:
        _baixar_uri(midia["uri"], destino)


def _img_input(caminho: Path) -> dict:
    mime = "image/png" if caminho.suffix.lower() == ".png" else "image/jpeg"
    return {"type": "image", "mime_type": mime, "data": base64.b64encode(caminho.read_bytes()).decode()}


# ---------------------------------------------------------------- imagens

def gerar_imagem(prompt: str, destino: Path, aspect_ratio: str = "9:16",
                 referencias: list[Path] | None = None) -> dict:
    entrada: list[dict] = [_img_input(p) for p in (referencias or [])]
    entrada.append({"type": "text", "text": prompt})
    body = {
        "model": MODELO_IMAGEM,
        "input": entrada,
        "response_format": {"type": "image", "mime_type": "image/jpeg",
                            "aspect_ratio": aspect_ratio, "image_size": "2K"},
    }
    resp = _com_retentativa(lambda: _req("POST", f"{BASE}/interactions", body, timeout=300,
                                         extra_headers={"Api-Revision": "2026-05-20"}))
    imgs = _midias(resp, "image")
    if not imgs:
        raise GeminiErro(f"Nenhuma imagem na resposta: {json.dumps(resp)[:800]}")
    _salvar(imgs[0], destino)
    return {"id": resp.get("id"), "modelo": MODELO_IMAGEM}


# ---------------------------------------------------------------- vídeo

def gerar_video(prompt: str, destino: Path, referencias: list[Path], duracao: int = 10,
                resolucao: str = "720p", aspect_ratio: str = "9:16") -> dict:
    if not 3 <= duracao <= 15:
        raise ValueError("Omni Flash aceita de 3 a 15 segundos por clipe")
    if len(referencias) > 6:
        raise ValueError("Omni Flash aceita no máximo 6 imagens de referência")
    entrada = [_img_input(p) for p in referencias] + [{"type": "text", "text": prompt}]
    body = {
        "model": MODELO_VIDEO,
        "input": entrada if referencias else prompt,
        "response_format": {"type": "video", "aspect_ratio": aspect_ratio,
                            "resolution": resolucao, "duration": f"{duracao}s",
                            "delivery": "uri"},
    }
    t0 = time.time()
    resp = _com_retentativa(lambda: _req("POST", f"{BASE}/interactions", body, timeout=1200))
    if resp.get("status") not in (None, "completed"):
        raise GeminiErro(f"Interação terminou com status {resp.get('status')}: {json.dumps(resp)[:800]}")
    videos = _midias(resp, "video")
    if not videos:
        raise GeminiErro(f"Nenhum vídeo na resposta (filtro de segurança?): {json.dumps(resp)[:800]}")
    _salvar(videos[0], destino)
    return {"id": resp.get("id"), "modelo": MODELO_VIDEO, "segundos_gerando": round(time.time() - t0),
            "custo_estimado_usd": round(PRECO_POR_SEGUNDO.get(resolucao, 0.07) * duracao, 3)}
