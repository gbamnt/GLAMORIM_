#!/usr/bin/env python3
"""Central de mini novelas para TikTok.

Uso:
  python central.py status     <serie>
  python central.py custo      <serie> <ep>
  python central.py personagens <serie> [--refazer clara,socorro]
  python central.py gerar      <serie> <ep> [--refazer c3] [--resolucao 720p] [--orcamento 10]
  python central.py editar     <serie> <ep> [--sem-legenda]
  python central.py episodio   <serie> <ep>        # gerar + editar + capa + legenda do post
  python central.py prompt     <serie> <ep> <cena> # mostra o prompt sem gastar nada

Os clipes já gerados nunca são refeitos sem --refazer (cada clipe custa dinheiro).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from estudio import editor, gemini
from estudio.serie import carregar, prompt_cena, prompt_retrato, IMGS_POR_PERSONAGEM


def _pasta_clipes(serie, n: int) -> Path:
    return serie.saida() / "clipes" / f"ep{n:02d}"


def cmd_status(a) -> None:
    s = carregar(a.serie)
    print(f"{s.titulo}")
    faltam = [p for p in s.personagens for r in s.refs_de(p) if not r.exists()]
    print(f"  retratos de referência: {'OK' if not faltam else 'faltam ' + str(len(faltam))}")
    for n in s.episodios_disponiveis():
        ep = s.episodio(n)
        pasta = _pasta_clipes(s, n)
        feitos = sum((pasta / f"{c['id']}.mp4").exists() for c in ep["cenas"])
        final = (s.saida() / f"ep{n:02d}.mp4").exists()
        print(f"  EP {n:2d} {ep['titulo']:<22} cenas {feitos}/{len(ep['cenas'])}"
              f"{'  ✓ pronto' if final else ''}")


def _custo(ep: dict, resolucao: str, so_faltando: Path | None = None) -> float:
    seg = sum(c["duracao"] for c in ep["cenas"]
              if so_faltando is None or not (so_faltando / f"{c['id']}.mp4").exists())
    return seg * gemini.PRECO_POR_SEGUNDO[resolucao]


def cmd_custo(a) -> None:
    s = carregar(a.serie)
    ep = s.episodio(a.ep)
    seg = sum(c["duracao"] for c in ep["cenas"])
    for r in ("720p", "1080p"):
        print(f"EP {a.ep}: {seg}s de vídeo em {r} ≈ US$ {_custo(ep, r):.2f}")


def cmd_prompt(a) -> None:
    s = carregar(a.serie)
    cena = next(c for c in s.episodio(a.ep)["cenas"] if c["id"] == a.cena)
    prompt, refs = prompt_cena(s, cena)
    print(prompt)
    print("\nReferências:", *[str(r.relative_to(s.pasta)) for r in refs], sep="\n  ")


def cmd_personagens(a) -> None:
    s = carregar(a.serie)
    refazer = set((a.refazer or "").split(",")) - {""}
    for pid in s.personagens:
        for i, destino in enumerate(s.refs_de(pid), start=1):
            if destino.exists() and pid not in refazer:
                continue
            print(f"  retrato {pid} #{i}…", flush=True)
            # O 2º retrato usa o 1º como referência, para manter o mesmo rosto.
            refs = [s.refs_de(pid)[0]] if i > 1 else []
            prompt = prompt_retrato(s, pid, i)
            if refs:
                prompt = "Same person as in the reference image (same face and hair). " + prompt
            gemini.gerar_imagem(prompt, destino, referencias=refs)
    print(f"Retratos em {s.pasta_personagens()}")


def cmd_gerar(a) -> None:
    s = carregar(a.serie)
    ep = s.episodio(a.ep)
    faltam = [r for c in ep["cenas"] for p in c.get("refs", []) for r in s.refs_de(p) if not r.exists()]
    if faltam:
        sys.exit(f"Faltam retratos de referência ({len(faltam)}). Rode: python central.py personagens {a.serie}")
    pasta = _pasta_clipes(s, a.ep)
    pasta.mkdir(parents=True, exist_ok=True)
    refazer = set((a.refazer or "").split(",")) - {""}
    for c in ep["cenas"]:
        if c["id"] in refazer:
            (pasta / f"{c['id']}.mp4").unlink(missing_ok=True)
    custo = _custo(ep, a.resolucao, pasta)
    print(f"EP {a.ep}: custo estimado desta rodada ≈ US$ {custo:.2f}")
    if custo > a.orcamento:
        sys.exit(f"Acima do orçamento de US$ {a.orcamento:.2f}. Use --orcamento para liberar.")
    for c in ep["cenas"]:
        destino = pasta / f"{c['id']}.mp4"
        if destino.exists():
            print(f"  {c['id']}: já existe, pulando")
            continue
        prompt, refs = prompt_cena(s, c)
        print(f"  {c['id']}: gerando {c['duracao']}s…", flush=True)
        try:
            info = gemini.gerar_video(prompt, destino, refs, duracao=c["duracao"], resolucao=a.resolucao)
        except gemini.GeminiErro as e:
            print(f"  {c['id']}: FALHOU — {e}")
            continue
        info["prompt"] = prompt
        (pasta / f"{c['id']}.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {c['id']}: ok em {info['segundos_gerando']}s (≈ US$ {info['custo_estimado_usd']})")


def cmd_editar(a) -> Path:
    s = carregar(a.serie)
    ep = s.episodio(a.ep)
    pasta = _pasta_clipes(s, a.ep)
    clipes = [pasta / f"{c['id']}.mp4" for c in ep["cenas"]]
    faltando = [c.name for c in clipes if not c.exists()]
    if faltando:
        sys.exit(f"Faltam clipes: {', '.join(faltando)}. Rode: python central.py gerar {a.serie} {a.ep}")
    destino = s.saida() / f"ep{a.ep:02d}.mp4"
    editor.montar_episodio(s, ep, clipes, destino, legendas=not a.sem_legenda)
    editor.gerar_capa(s, ep, clipes[-1], destino.with_name(f"ep{a.ep:02d}_capa.jpg"))
    post = (f"{ep['legenda_tiktok']}\n\n"
            + " ".join("#" + h for h in ep.get("hashtags", [])) + "\n")
    destino.with_name(f"ep{a.ep:02d}_post.txt").write_text(post, encoding="utf-8")
    print(f"Pronto: {destino}  ({editor.duracao(destino):.1f}s)")
    return destino


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nome in ("status", "personagens"):
        p = sub.add_parser(nome)
        p.add_argument("serie")
        if nome == "personagens":
            p.add_argument("--refazer")
    for nome in ("custo", "gerar", "editar", "episodio"):
        p = sub.add_parser(nome)
        p.add_argument("serie")
        p.add_argument("ep", type=int)
        p.add_argument("--refazer", help="ids de cenas separados por vírgula")
        p.add_argument("--resolucao", default="720p", choices=list(gemini.PRECO_POR_SEGUNDO))
        p.add_argument("--orcamento", type=float, default=10.0, help="limite em US$ por rodada")
        p.add_argument("--sem-legenda", action="store_true")
    p = sub.add_parser("prompt")
    p.add_argument("serie")
    p.add_argument("ep", type=int)
    p.add_argument("cena")
    a = ap.parse_args()
    if a.cmd == "episodio":
        cmd_gerar(a)
        cmd_editar(a)
    else:
        {"status": cmd_status, "custo": cmd_custo, "prompt": cmd_prompt, "personagens": cmd_personagens,
         "gerar": cmd_gerar, "editar": cmd_editar}[a.cmd](a)


if __name__ == "__main__":
    main()
