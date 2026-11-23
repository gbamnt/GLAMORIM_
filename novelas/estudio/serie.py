"""Carrega a bíblia e os episódios, valida e monta os prompts de cada cena."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
SERIES = RAIZ / "series"
SAIDA = RAIZ / "saida"
FONTES = RAIZ / "assets" / "fonts"

MAX_PERSONAGENS_REF = 2   # limite do Omni Flash: 3 imagens por personagem, 2 personagens
IMGS_POR_PERSONAGEM = 2


@dataclass
class Serie:
    slug: str
    pasta: Path
    biblia: dict

    @property
    def titulo(self) -> str:
        return self.biblia["serie"]["titulo"]

    @property
    def personagens(self) -> dict:
        return self.biblia["personagens"]

    def pasta_personagens(self) -> Path:
        return self.pasta / "personagens"

    def refs_de(self, pid: str) -> list[Path]:
        return [self.pasta_personagens() / f"{pid}_{i}.jpg" for i in range(1, IMGS_POR_PERSONAGEM + 1)]

    def episodio(self, n: int) -> dict:
        ep = yaml.safe_load((self.pasta / "episodios" / f"ep{n:02d}.yaml").read_text(encoding="utf-8"))
        validar_episodio(self, ep)
        return ep

    def episodios_disponiveis(self) -> list[int]:
        return sorted(int(p.stem[2:]) for p in (self.pasta / "episodios").glob("ep*.yaml"))

    def saida(self) -> Path:
        return SAIDA / self.slug


def carregar(slug: str) -> Serie:
    pasta = SERIES / slug
    biblia = yaml.safe_load((pasta / "biblia.yaml").read_text(encoding="utf-8"))
    return Serie(slug=slug, pasta=pasta, biblia=biblia)


def validar_episodio(serie: Serie, ep: dict) -> None:
    erros = []
    for c in ep["cenas"]:
        cid = c.get("id", "?")
        if not 3 <= int(c["duracao"]) <= 15:
            erros.append(f"{cid}: duração {c['duracao']}s fora de 3–15 s")
        if c["cenario"] not in serie.biblia["cenarios"]:
            erros.append(f"{cid}: cenário desconhecido '{c['cenario']}'")
        refs = c.get("refs", [])
        if len(refs) > MAX_PERSONAGENS_REF:
            erros.append(f"{cid}: no máximo {MAX_PERSONAGENS_REF} personagens com imagem de referência")
        for f in c.get("falas", []):
            if f["quem"] not in serie.personagens:
                erros.append(f"{cid}: personagem desconhecido '{f['quem']}'")
            if f["t"] >= c["duracao"]:
                erros.append(f"{cid}: fala em t={f['t']} depois do fim da cena")
        for p in refs:
            if p not in serie.personagens:
                erros.append(f"{cid}: ref desconhecida '{p}'")
    if erros:
        raise ValueError(f"Episódio {ep.get('numero')} inválido:\n  " + "\n  ".join(erros))


def _fmt_t(t: float) -> str:
    return f"{t:g}s"


def prompt_retrato(serie: Serie, pid: str, variante: int) -> str:
    p = serie.personagens[pid]
    if variante == 1:
        enquadramento = ("Cinematic vertical portrait, head and shoulders, facing the camera, "
                         "neutral soft-grey studio background, soft key light")
    else:
        enquadramento = f"Cinematic vertical photo, {p['retrato_extra']}"
    return (f"{enquadramento}. {p['visual'].strip()} Photorealistic, natural skin texture, "
            "shot on a full-frame cinema camera, 85mm lens, telenovela character reference photo. "
            "Exactly one person in the image. No text, no watermark.")


def prompt_cena(serie: Serie, cena: dict) -> tuple[str, list[Path]]:
    """Monta o prompt (inglês + falas em pt-BR) e a lista de imagens de referência."""
    b = serie.biblia
    partes = [b["estilo"].strip()]
    imagens: list[Path] = []
    descr_refs = []
    for pid in cena.get("refs", []):
        refs = serie.refs_de(pid)
        ini = len(imagens) + 1
        imagens += refs
        fim = len(imagens)
        descr_refs.append(
            f"Reference images {ini}-{fim} show {serie.personagens[pid]['nome']}; keep this character's face, "
            f"hair, body and outfit exactly as in those images. {serie.personagens[pid]['visual'].strip()}")
    if descr_refs:
        partes.append("CHARACTERS: " + " ".join(descr_refs))
    if cena.get("figurantes"):
        partes.append("OTHER PEOPLE: " + cena["figurantes"].strip())
    partes.append("SETTING: " + b["cenarios"][cena["cenario"]].strip() + ".")
    partes.append("ACTION: " + cena["acao"].strip())
    falas = cena.get("falas", [])
    if falas:
        linhas = [f'At {_fmt_t(f["t"])}, {serie.personagens[f["quem"]]["nome"]} says ({f.get("tom", "naturally")}), '
                  f'in Brazilian Portuguese: "{f["texto"]}"' for f in falas]
        partes.append("DIALOGUE (speak exactly these words, in Brazilian Portuguese, lip-synced): "
                      + " ".join(linhas) + " No other dialogue.")
    else:
        partes.append("No dialogue.")
    partes.append(f"The clip lasts {cena['duracao']} seconds. Keep the vertical 9:16 composition with faces "
                  "in the upper-middle part of the frame.")
    return "\n\n".join(partes), imagens
