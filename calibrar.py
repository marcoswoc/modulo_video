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

Rotulagem (heuristica por SEGMENTO do caminho do arquivo)
    - segmento 'gpp' / 'backpain' / 'parkinson' / 'stroke' -> 'paciente'
    - segmento 'cg' / 'control' / 'healthy'                -> 'saudavel'
    - caso contrario                                       -> 'desconhecido'

Estrutura esperada do KIMORE (confira antes de processar com --listar):
    KIMORE/CG/...   (Control Group  -> saudavel)
    KIMORE/GPP/BackPain|Parkinson|Stroke/...  (pacientes)

Dica: rode primeiro em modo dry-run para validar a rotulagem sem processar:
    python calibrar.py --raiz KIMORE --listar
"""

from __future__ import annotations

import argparse
import csv
import os

from config import LIMIARES

# Obs.: os imports pesados (cv2/mediapipe via src.pose_extractor) sao feitos
# preguicosamente dentro de main(), apos o modo --listar. Assim o dry-run de
# validacao da estrutura de pastas roda mesmo sem essas dependencias instaladas.

EXTENSOES_VIDEO = (".mp4", ".avi", ".mov", ".mkv")

# Tokens (por segmento de caminho) usados para inferir o grupo de cada video.
# KIMORE usa as pastas de topo 'CG' (saudaveis) e 'GPP' (pacientes), com
# subpastas BackPain/Parkinson/Stroke dentro de GPP.
TOKENS_PACIENTE = ("gpp", "backpain", "parkinson", "stroke")
TOKENS_SAUDAVEL = ("cg", "control", "controlgroup", "healthy")

# Metricas biomecanicas que possuem limiar em config.py (as que calibramos).
METRICAS = [
    "inclinacao_tronco_graus",
    "assimetria_marcha",
    "instabilidade_lateral",
    "velocidade",
]


def _tokens_caminho(caminho: str) -> set[str]:
    """Quebra o caminho em tokens (segmentos e pedacos separados por _ ou -).

    Trabalha com '/' (Colab/Linux) e '\\' (Windows) e evita falso positivo de
    substring (ex.: 'cg' dentro de 'encoding') ao casar por token, nao por trecho.
    """
    normalizado = caminho.replace("\\", "/").lower()
    tokens: set[str] = set()
    for segmento in normalizado.split("/"):
        tokens.add(segmento)
        for pedaco in segmento.replace("-", "_").split("_"):
            tokens.add(pedaco)
    return tokens


def rotular(caminho: str) -> str:
    """Infere o grupo (saudavel/paciente) a partir do caminho do arquivo."""
    tokens = _tokens_caminho(caminho)
    if tokens & set(TOKENS_PACIENTE):
        return "paciente"
    if tokens & set(TOKENS_SAUDAVEL):
        return "saudavel"
    return "desconhecido"


def listar_videos(raiz: str, filtro_nome: str = "") -> list[str]:
    """Encontra todos os videos abaixo de 'raiz' (recursivo).

    filtro_nome: se informado, mantem apenas arquivos cujo nome contenha esse
    texto (ex.: 'rgb' para ignorar videos de depth). Comparacao sem maiusculas.
    """
    filtro = filtro_nome.lower()
    achados = []
    for pasta, _subpastas, arquivos in os.walk(raiz):
        for nome in arquivos:
            if not nome.lower().endswith(EXTENSOES_VIDEO):
                continue
            if filtro and filtro not in nome.lower():
                continue
            achados.append(os.path.join(pasta, nome))
    return sorted(achados)


def resumo_grupos(videos: list[str]) -> dict[str, int]:
    """Conta quantos videos caem em cada grupo inferido pela rotulagem."""
    contagem = {"saudavel": 0, "paciente": 0, "desconhecido": 0}
    for v in videos:
        contagem[rotular(v)] += 1
    return contagem


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
    parser.add_argument("--filtro-nome", default="",
                        help="Mantem so arquivos cujo nome contenha este texto (ex.: rgb)")
    parser.add_argument("--listar", action="store_true",
                        help="Dry-run: lista videos e rotulo inferido SEM processar (valida a estrutura de pastas)")
    args = parser.parse_args()

    videos = listar_videos(args.raiz, filtro_nome=args.filtro_nome)
    if args.max > 0:
        videos = videos[: args.max]
    if not videos:
        print(f"Nenhum video encontrado em: {args.raiz}")
        return

    contagem = resumo_grupos(videos)

    # Modo dry-run: so lista e sai. Serve para conferir a rotulagem CG/GPP antes
    # de gastar tempo com a extracao de pose.
    if args.listar:
        print(f"Encontrados {len(videos)} videos em: {args.raiz}\n")
        for v in videos:
            print(f"  {rotular(v):12s} {v}")
        print(f"\n===== RESUMO POR GRUPO =====")
        for grupo, n in contagem.items():
            print(f"  {grupo:12s}: {n}")
        if contagem["desconhecido"]:
            print("\nAVISO: ha videos 'desconhecido' (fora de CG/GPP). Confira a")
            print("estrutura de pastas ou ajuste TOKENS_SAUDAVEL/TOKENS_PACIENTE.")
        if contagem["saudavel"] == 0 or contagem["paciente"] == 0:
            print("\nAVISO: falta pelo menos um grupo. A calibracao precisa dos DOIS")
            print("(saudavel e paciente) para comparar e sugerir limiares.")
        return

    # Imports pesados so aqui: quem chega neste ponto vai de fato processar.
    from src.pose_extractor import extrair_pose
    from src.biomechanics import extrair_metricas

    print(f"Encontrados {len(videos)} videos "
          f"(saudavel={contagem['saudavel']}, paciente={contagem['paciente']}, "
          f"desconhecido={contagem['desconhecido']}).")
    print(f"Processando (pular_frames={args.pular_frames})...\n")

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
