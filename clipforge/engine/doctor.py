"""Diagnóstico do ambiente: `python clipforge.py doctor`."""
from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from . import config as cfgmod

OK, FALHA = "✔", "✘"


@dataclass
class Item:
    nome: str
    ok: bool
    detalhe: str = ""
    correcao: str = ""
    obrigatorio: bool = True


def _run(cmd: list[str], timeout: float = 20) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def checar_python() -> Item:
    v = sys.version_info
    ok = v >= (3, 11)
    return Item("Python ≥ 3.11", ok, f"{platform.python_version()} ({sys.executable})",
                "Instale Python 3.11+: winget install Python.Python.3.12")


def checar_binario(nome: str) -> Item:
    caminho = shutil.which(nome)
    detalhe = ""
    if caminho:
        primeira = _run([caminho, "-version"]).splitlines()
        detalhe = primeira[0][:70] if primeira else caminho
    return Item(f"{nome} no PATH", bool(caminho), detalhe,
                "winget install Gyan.FFmpeg  (depois feche e reabra o terminal)")


def checar_filtro_ass() -> Item:
    ff = shutil.which("ffmpeg")
    if not ff:
        return Item("FFmpeg com filtro 'ass' (libass)", False, "ffmpeg ausente",
                    "winget install Gyan.FFmpeg")
    try:
        saida = _run([ff, "-hide_banner", "-filters"])
    except Exception as e:  # noqa: BLE001
        return Item("FFmpeg com filtro 'ass' (libass)", False, str(e), "Reinstale o FFmpeg (build full)")
    ok = any(len(p := l.split()) >= 2 and p[1] == "ass" for l in saida.splitlines())
    return Item("FFmpeg com filtro 'ass' (libass)", ok, "" if ok else "filtro não encontrado",
                "Use a build 'full' do FFmpeg: winget install Gyan.FFmpeg")


def checar_modulo(mod: str, pip: str) -> Item:
    achou = importlib.util.find_spec(mod) is not None
    detalhe = ""
    if achou:
        try:
            m = __import__(mod)
            detalhe = f"versão {getattr(m, '__version__', '?')}"
        except Exception as e:  # noqa: BLE001
            achou, detalhe = False, f"falha ao importar: {e}"[:90]
    return Item(f"módulo {mod}", achou, detalhe, f"pip install -r requirements.txt  (ou: pip install \"{pip}\")")


def checar_haar() -> Item:
    nome = "Haar cascade (frontalface_default)"
    correcao = 'pip uninstall -y opencv-python-headless && pip install "opencv-python-headless<5"'
    try:
        import cv2  # type: ignore
    except Exception:  # noqa: BLE001
        return Item(nome, False, "cv2 indisponível", correcao)
    base = getattr(getattr(cv2, "data", None), "haarcascades", "")
    arq = Path(base) / "haarcascade_frontalface_default.xml" if base else None
    ok = bool(arq and arq.exists())
    if ok:
        ok = not cv2.CascadeClassifier(str(arq)).empty()
    return Item(nome, ok, str(arq) if ok else f"não encontrado (OpenCV {cv2.__version__})", correcao)


def checar_gemini(cfg: dict) -> Item:
    chave = cfgmod.chave_gemini(cfg)
    origem = "variável GEMINI_API_KEY" if os.environ.get("GEMINI_API_KEY", "").strip() else "config.local.json"
    return Item("Chave Gemini", bool(chave), f"configurada via {origem}" if chave else "não configurada",
                'Gere grátis em aistudio.google.com e salve em config.local.json: '
                '{"llm":{"gemini":{"chave":"SUA_CHAVE"}}}  (ou use o modo heurística/Ollama)',
                obrigatorio=False)


def checar_ollama(cfg: dict) -> Item:
    oc = cfg.get("llm", {}).get("ollama", {})
    url = oc.get("url", "http://127.0.0.1:11434").rstrip("/")
    modelo = oc.get("modelo", "")
    nome = "Ollama local"
    try:
        with urllib.request.urlopen(f"{url}/api/tags", timeout=2) as r:
            dados = json.load(r)
    except Exception:  # noqa: BLE001
        return Item(nome, False, f"sem resposta em {url}",
                    "Opcional: winget install Ollama.Ollama  e depois  ollama pull " + (modelo or "qwen2.5:7b"),
                    obrigatorio=False)
    nomes = [m.get("name", "") for m in dados.get("models", [])]
    tem = any(n == modelo or n.split(":")[0] == modelo for n in nomes)
    return Item(nome, tem, f"ativo; modelo '{modelo}' {'instalado' if tem else 'ausente'}",
                f"ollama pull {modelo}", obrigatorio=False)


def _hf_cache() -> Path:
    if os.environ.get("HF_HUB_CACHE"):
        return Path(os.environ["HF_HUB_CACHE"])
    if os.environ.get("HF_HOME"):
        return Path(os.environ["HF_HOME"]) / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def checar_modelo_whisper(cfg: dict) -> Item:
    modelo = cfg.get("whisper", {}).get("modelo", "small")
    nome = f"Modelo Whisper '{modelo}' baixado"
    p = Path(modelo)
    if p.is_dir():  # caminho local para o modelo
        ok = (p / "model.bin").exists()
        return Item(nome, ok, str(p), "Pasta do modelo sem model.bin", obrigatorio=False)
    repo = _hf_cache() / f"models--Systran--faster-whisper-{modelo}" / "snapshots"
    ok = repo.is_dir() and any((s / "model.bin").exists() for s in repo.iterdir())
    return Item(nome, ok, str(repo.parent) if ok else "ainda não baixado",
                f'Baixa sozinho na 1ª transcrição, ou agora: python -c "from faster_whisper import WhisperModel; '
                f"WhisperModel('{modelo}', device='cpu', compute_type='int8')\"",
                obrigatorio=False)


def executar() -> int:
    cfg = cfgmod.carregar()
    itens = [
        checar_python(),
        checar_binario("ffmpeg"),
        checar_binario("ffprobe"),
        checar_filtro_ass(),
        checar_modulo("faster_whisper", "faster-whisper"),
        checar_modulo("cv2", "opencv-python-headless<5"),
        checar_modulo("numpy", "numpy"),
        checar_haar(),
        checar_modelo_whisper(cfg),
        checar_gemini(cfg),
        checar_ollama(cfg),
    ]
    print("ClipForge — diagnóstico\n")
    for it in itens:
        marca = OK if it.ok else FALHA
        tag = "" if it.obrigatorio else " (opcional)"
        print(f" {marca} {it.nome}{tag}" + (f" — {it.detalhe}" if it.detalhe else ""))
        if not it.ok:
            print(f"     → {it.correcao}")
    falhas = [i for i in itens if i.obrigatorio and not i.ok]
    opc = [i for i in itens if not i.obrigatorio and not i.ok]
    print()
    if falhas:
        print(f"{len(falhas)} item(ns) obrigatório(s) com problema. Corrija e rode de novo.")
        return 1
    msg = "Tudo pronto para rodar."
    if opc:
        msg += f" ({len(opc)} item(ns) opcional(is) ausente(s): o modo heurística funciona sem eles.)"
    print(msg)
    return 0
