"""Edição com ffmpeg: junta as cenas, legenda, gancho, cartela final, áudio e capa.

Saída pronta para o TikTok: 1080x1920, 30 fps, H.264 + AAC, áudio normalizado (-14 LUFS).
Os textos ficam fora das zonas cobertas pela interface do TikTok (topo, rodapé e
coluna de botões à direita).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .serie import FONTES, Serie

W, H, FPS = 1080, 1920, 30


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou:\n{' '.join(cmd)}\n{r.stderr[-3000:]}")


def duracao(arq: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "json", str(arq)], capture_output=True, text=True, check=True)
    return float(json.loads(r.stdout)["format"]["duration"])


def tem_audio(arq: Path) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                        "stream=index", "-of", "csv=p=0", str(arq)], capture_output=True, text=True)
    return bool(r.stdout.strip())


def normalizar(entrada: Path, saida: Path) -> None:
    """Padroniza cada clipe: 1080x1920 (crop central), 30 fps, áudio estéreo 48 kHz."""
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
          f"crop={W}:{H},fps={FPS},setsar=1,format=yuv420p")
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(entrada)]
    if not tem_audio(entrada):
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest"]
    cmd += ["-map", "0:v:0", "-map", "0:a:0" if tem_audio(entrada) else "1:a:0",
            "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "17",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", str(saida)]
    _run(cmd)


# ------------------------------------------------------------------ ASS

def _t(s: float) -> str:
    s = max(0.0, s)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{sec:05.2f}"


def _esc(txt: str) -> str:
    return txt.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", "\\N")


ASS_CABECALHO = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Fala,Inter,66,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,5,2,2,110,170,560,1
Style: Gancho,Inter,72,&H00000000,&H00000000,&H0000D7FF,&H0000D7FF,1,0,0,0,100,100,0,0,3,22,0,8,90,90,330,1
Style: Tag,Inter,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,1,0,3,12,0,8,90,90,230,1
Style: Fim,Inter,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,6,3,5,90,90,0,1
Style: FimSub,Inter,52,&H0000D7FF,&H0000D7FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,4,2,5,90,90,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _evento(ini: float, fim: float, estilo: str, texto: str, extra: str = "") -> str:
    return f"Dialogue: 0,{_t(ini)},{_t(fim)},{estilo},,0,0,0,,{extra}{_esc(texto)}\n"


def montar_ass(serie: Serie, ep: dict, duracoes: list[float], total: float, cartela: float,
               legendas: bool = True) -> str:
    ass = ASS_CABECALHO
    n = ep["numero"]
    # Etiqueta da série/episódio no topo durante todo o episódio.
    ass += _evento(0, total, "Tag", f"{serie.titulo.upper()}  ·  EP {n}")
    # Gancho de abertura (2,8 s), com entrada rápida.
    if ep.get("gancho_abertura"):
        ass += _evento(0.1, 2.9, "Gancho", ep["gancho_abertura"], r"{\fad(120,200)}")
    # Legendas das falas, posicionadas pelo tempo de cada fala no roteiro.
    if legendas:
        offset = 0.0
        for cena, dur in zip(ep["cenas"], duracoes):
            falas = sorted(cena.get("falas", []), key=lambda f: f["t"])
            for i, f in enumerate(falas):
                ini = offset + float(f["t"])
                prox = offset + float(falas[i + 1]["t"]) if i + 1 < len(falas) else offset + dur
                fim = min(prox - 0.05, ini + max(1.8, len(f["texto"]) / 13 + 0.8), offset + dur - 0.05)
                ass += _evento(ini, fim, "Fala", f["texto"])
            offset += dur
    # Cartela final ("Parte N+1").
    fim_ini = total - cartela
    ass += _evento(fim_ini, total, "Fim", f"PARTE {n + 1}", r"{\fad(250,0)\pos(540,860)}")
    ass += _evento(fim_ini, total, "FimSub", "Segue pra não perder o próximo episódio",
                   r"{\fad(400,0)\pos(540,990)}")
    return ass


# ------------------------------------------------------------------ episódio

def montar_episodio(serie: Serie, ep: dict, clipes: list[Path], destino: Path,
                    legendas: bool = True, cartela: float = 2.5) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        norm = []
        for i, c in enumerate(clipes):
            out = tmp / f"n{i:02d}.mp4"
            normalizar(c, out)
            norm.append(out)
        duracoes = [duracao(p) for p in norm]

        # Cartela final: último quadro congelado e escurecido, com o áudio em fade.
        ultimo = tmp / "cartela.mp4"
        _run(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.1", "-i", str(norm[-1]),
              "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
              "-filter_complex", f"[0:v]trim=end_frame=1,loop=loop={int(cartela * FPS)}:size=1:start=0,"
              f"setpts=N/{FPS}/TB,eq=brightness=-0.25:saturation=0.6,boxblur=6,fps={FPS},format=yuv420p[v]",
              "-map", "[v]", "-map", "1:a", "-t", f"{cartela}", "-c:v", "libx264", "-crf", "17",
              "-c:a", "aac", "-ar", "48000", "-ac", "2", str(ultimo)])
        partes = norm + [ultimo]
        total = sum(duracoes) + cartela

        ass = tmp / "textos.ass"
        ass.write_text(montar_ass(serie, ep, duracoes, total, cartela, legendas), encoding="utf-8")

        entradas: list[str] = []
        for p in partes:
            entradas += ["-i", str(p)]
        k = len(partes)
        concat = "".join(f"[{i}:v][{i}:a]" for i in range(k)) + f"concat=n={k}:v=1:a=1[cv][ca]"
        fontes = str(FONTES).replace(":", r"\:")
        filtro = (f"{concat};[cv]subtitles='{ass}':fontsdir='{fontes}'[v];"
                  f"[ca]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
        _run(["ffmpeg", "-y", "-v", "error", *entradas, "-filter_complex", filtro,
              "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
              "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac",
              "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(destino)])
        shutil.copy(ass, destino.with_suffix(".ass"))
    return destino


def gerar_capa(serie: Serie, ep: dict, clipe: Path, destino: Path, momento: float = 1.5) -> Path:
    """Capa 1080x1920 com o título do episódio (usar como 'capa' no TikTok)."""
    fonte = str(FONTES / "Inter-Black.otf").replace(":", r"\:")
    titulo = ep["titulo"].upper().replace("'", "’").replace(":", r"\:")
    serie_t = serie.titulo.upper().replace("'", "’").replace(":", r"\:")
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"drawbox=y=ih*0.58:w=iw:h=ih*0.42:color=black@0.55:t=fill,"
          f"drawtext=fontfile='{fonte}':text='EP {ep['numero']}':fontsize=90:fontcolor=0xFFD700:"
          f"x=(w-tw)/2:y=h*0.62,"
          f"drawtext=fontfile='{fonte}':text='{titulo}':fontsize=104:fontcolor=white:"
          f"borderw=4:bordercolor=black:x=(w-tw)/2:y=h*0.62+120,"
          f"drawtext=fontfile='{fonte}':text='{serie_t}':fontsize=48:fontcolor=white@0.9:"
          f"x=(w-tw)/2:y=h*0.62+270")
    _run(["ffmpeg", "-y", "-v", "error", "-ss", str(momento), "-i", str(clipe), "-frames:v", "1",
          "-vf", vf, "-q:v", "2", str(destino)])
    return destino
