"""
calibrar.py
-----------
Ferramenta de CALIBRACAO dos limiares clinicos usando um dataset de video RGB
(ex.: KIMORE). Roda a extracao de pose + metricas biomecanicas em varios videos,
rotula cada video pelo grupo (saudavel x paciente) inferido do caminho, salva
um CSV com as metricas por video e imprime um comparativo entre os grupos,
com sugestoes de limiar baseadas nos dados.

Por que isso importa
--------------------
Os limiares em config.py (ex.: inclinacao > 15 graus) sao chutes iniciais.
Rodando o modulo em pacientes reais, voce ve a distribuicao real das metricas
e ajusta os cortes para separarem de fato "normal" de "anormal". Isso da rigor
ao trabalho e gera os "resultados obtidos" que o relatorio exige.

Uso
---
    python calibrar.py --raiz caminho/para/KIMORE
    python calibrar.py --raiz KIMORE --pular-frames 5 --max 40 --saida-csv data/exemplos/calibracao.csv

Rotulagem (heuristica pelo caminho do arquivo)
    - contem 'gpp' / 'backpain' / 'parkinson' / 'stroke' -> 'paciente'
    - contem 'cg' / 'control'                            -> 'saudavel'
    - caso contrario                                     -> 'desconhecido'
"""

from __future__ import annotations

import argparse
import csv
import os

from src.pose_extractor import extrair_pose
from src.biomechanics import extrair_metricas
from config import LIMIARES

EXTENSOES_VIDEO = (".mp4", ".avi", ".mov", ".mkv")

# Metricas biomecanicas que possuem limiar em config.py (as que calibramos).
METRICAS = [
    "inclinacao_tronco_graus",
    "assimetria_marcha",
    "instabilidade_lateral",
    "velocidade",
]


def rotular(caminho: str) -> str:
    """Infere o grupo (saudavel/paciente) a partir do caminho do arquivo."""
    p = caminho.lower()
    if any(k in p for k in ("gpp", "backpain", "back_pain", "parkinson", "stroke")):
        return "paciente"
    if "cg" in p or "control" in p:
        return "saudavel"
    return "desconhecido"


def listar_videos(raiz: str) -> list[str]:
    """Encontra todos os videos abaixo de 'raiz' (recursivo)."""
    achados = []
    for pasta, _subpastas, arquivos in os.walk(raiz):
        for nome in arquivos:
            if nome.lower().endswith(EXTENSOES_VIDEO):
                achados.append(os.path.join(pasta, nome))
    return sorted(achados)


def _percentil(valores: list[float], p: float) -> float:
    """Percentil simples (0..100) por interpolacao linear."""
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    if len(ordenados) == 1:
        return ordenados[0]
    pos = (p / 100.0) * (len(ordenados) - 1)
    baixo = int(pos)
    frac = pos - baixo
    if baixo + 1 >= len(ordenados):
        return ordenados[-1]
    return ordenados[baixo] + frac * (ordenados[baixo + 1] - ordenados[baixo])


def _media(valores: list[float]) -> float:
    return sum(valores) / len(valores) if valores else 0.0


def resumir_grupo(linhas: list[dict], grupo: str, metrica: str) -> dict:
    """Estatisticas de uma metrica para um grupo."""
    valores = [float(l[metrica]) for l in linhas if l["grupo"] == grupo and l[metrica] != ""]
    return {
        "n": len(valores),
        "media": _media(valores),
        "mediana": _percentil(valores, 50),
        "p90": _percentil(valores, 90),
        "valores": valores,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibracao de limiares com dataset de video RGB")
    parser.add_argument("--raiz", required=True, help="Pasta raiz do dataset (ex.: KIMORE)")
    parser.add_argument("--saida-csv", default="data/saida/calibracao.csv",
                        help="Caminho do CSV de saida com as metricas por video")
    parser.add_argument("--pular-frames", type=int, default=5,
                        help="Processa 1 a cada N frames (acelera em CPU). Padrao: 5")
    parser.add_argument("--max", type=int, default=0,
                        help="Limita o numero de videos (0 = todos). Util para teste rapido")
    args = parser.parse_args()

    videos = listar_videos(args.raiz)
    if args.max > 0:
        videos = videos[: args.max]
    if not videos:
        print(f"Nenhum video encontrado em: {args.raiz}")
        return

    print(f"Encontrados {len(videos)} videos. Processando (pular_frames={args.pular_frames})...\n")

    linhas: list[dict] = []
    for i, video in enumerate(videos, 1):
        grupo = rotular(video)
        try:
            registros = extrair_pose(video, pular_frames=args.pular_frames)
            metricas = extrair_metricas(registros)
        except Exception as e:  # noqa: BLE001 - queremos continuar o lote
            print(f"[{i}/{len(videos)}] ERRO em {os.path.basename(video)}: {e}")
            continue

        linha = {"video": video, "grupo": grupo, "frames_validos": metricas.get("frames_validos", 0)}
        for m in METRICAS:
            linha[m] = round(float(metricas.get(m, 0.0)), 4)
        linhas.append(linha)
        print(f"[{i}/{len(videos)}] {grupo:12s} {os.path.basename(video)}  "
              + "  ".join(f"{m}={linha[m]}" for m in METRICAS))

    if not linhas:
        print("\nNenhuma metrica extraida. Verifique os videos.")
        return

    # Salva o CSV por video.
    os.makedirs(os.path.dirname(args.saida_csv) or ".", exist_ok=True)
    campos = ["video", "grupo", "frames_validos"] + METRICAS
    with open(args.saida_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(linhas)
    print(f"\nCSV salvo em: {args.saida_csv}")

    # Comparativo saudavel x paciente + sugestao de limiar.
    print("\n===== COMPARATIVO POR GRUPO =====")
    for m in METRICAS:
        s = resumir_grupo(linhas, "saudavel", m)
        p = resumir_grupo(linhas, "paciente", m)
        atual = LIMIARES.get(m, LIMIARES.get(f"{m}_graus"))
        print(f"\n# {m}   (limiar atual em config: {atual})")
        print(f"  saudavel: n={s['n']:3d}  media={s['media']:.3f}  mediana={s['mediana']:.3f}  p90={s['p90']:.3f}")
        print(f"  paciente: n={p['n']:3d}  media={p['media']:.3f}  mediana={p['mediana']:.3f}  p90={p['p90']:.3f}")
        # Sugestao: corte no p90 dos saudaveis (a maioria dos normais fica abaixo).
        if s["n"] >= 3:
            print(f"  -> sugestao de limiar (p90 dos saudaveis): {s['p90']:.3f}")
        else:
            print("  -> poucos saudaveis para sugerir; junte mais videos do grupo CG.")

    print("\nDica: use a sugestao como ponto de partida e confira se ela separa bem")
    print("saudaveis de pacientes olhando o CSV. Ajuste os valores em config.py.")


if __name__ == "__main__":
    main()
