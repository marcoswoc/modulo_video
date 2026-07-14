"""
calibrar.py
-----------
Ferramenta de CALIBRACAO dos limiares clinicos usando o dataset REHAB24-6
(video RGB publico de exercicios de reabilitacao, Zenodo).

Ideia: o REHAB24-6 traz um `Segmentation.csv` com UMA LINHA POR REPETICAO de
exercicio, cada uma com um rotulo binario `correctness` (1 = execucao correta,
0 = execucao incorreta) e a janela de frames [first_frame, last_frame]. Rodamos
a extracao de pose + metricas biomecanicas em cada repeticao, agrupamos por
correto x incorreto e comparamos as distribuicoes, sugerindo limiares para
config.py.

Por que isso importa
--------------------
Os limiares em config.py (ex.: inclinacao > 15 graus) sao chutes iniciais.
Vendo a distribuicao real das metricas em execucoes CORRETAS x INCORRETAS,
ajustamos os cortes para separarem de fato "normal" de "anomalo". Isso da rigor
ao trabalho e gera os "resultados obtidos" que o relatorio exige.

Estrutura esperada (REHAB24-6, https://zenodo.org/records/13305826)
    <raiz>/
        Segmentation.csv        (sep=';', 1 linha por repeticao)
        <videos RGB>            (duas cameras: Camera17 horizontal, Camera18 vertical)
    Colunas do CSV: video_id;repetition_number;exercise_id;person_id;first_frame;
    last_frame;cam17_orientation;mocap_erroneous;exercise_subtype;lights_on;
    extra_person_in_cam17;extra_person_in_cam18;correctness

Uso
---
    # 1) valida CSV + matching de video (dry-run, nao processa, nao exige cv2):
    python calibrar.py --raiz caminho/para/REHAB24-6 --listar

    # 2) processa e sugere limiares (recomendado focar 1 exercicio por vez):
    python calibrar.py --raiz caminho/para/REHAB24-6 --exercise 6 --pular-frames 3

    # fixar uma camera se houver mais de um video por gravacao:
    python calibrar.py --raiz caminho/para/REHAB24-6 --camera Camera18 --listar
"""

from __future__ import annotations

import argparse
import csv
import os

from config import LIMIARES

# Obs.: os imports pesados (cv2/mediapipe via src.pose_extractor) sao feitos
# preguicosamente dentro de processar(), apos o modo --listar. Assim o dry-run
# de validacao roda mesmo sem essas dependencias instaladas.

EXTENSOES_VIDEO = (".mp4", ".avi", ".mov", ".mkv")

# Nome padrao do arquivo de anotacao do REHAB24-6.
CSV_ANOTACAO = "Segmentation.csv"

# Metricas biomecanicas que possuem limiar em config.py (as que calibramos).
METRICAS = [
    "inclinacao_tronco_graus",
    "assimetria_marcha",
    "instabilidade_lateral",
    "velocidade",
]


def rotulo(correctness: int) -> str:
    """1 -> 'correto', 0 -> 'incorreto'."""
    return "correto" if int(correctness) == 1 else "incorreto"


def carregar_anotacoes(caminho_csv: str, exercicio: int | None = None) -> list[dict]:
    """Le o Segmentation.csv (sep=';') e devolve uma lista de repeticoes.

    Cada item vira um dict com os campos ja convertidos para int onde faz sentido.
    Se 'exercicio' for informado, mantem apenas as linhas daquele exercise_id.
    """
    linhas: list[dict] = []
    with open(caminho_csv, newline="", encoding="utf-8-sig") as f:
        leitor = csv.DictReader(f, delimiter=";")
        for reg in leitor:
            try:
                item = {
                    "video_id": reg["video_id"].strip(),
                    "repetition_number": int(reg["repetition_number"]),
                    "exercise_id": int(reg["exercise_id"]),
                    "person_id": int(reg["person_id"]),
                    "first_frame": int(reg["first_frame"]),
                    "last_frame": int(reg["last_frame"]),
                    "correctness": int(reg["correctness"]),
                }
            except (KeyError, ValueError) as e:
                raise ValueError(
                    f"Linha invalida no CSV ({e}). Confira se o separador e ';' e se "
                    f"as colunas batem com o Segmentation.csv do REHAB24-6."
                )
            if exercicio is not None and item["exercise_id"] != exercicio:
                continue
            linhas.append(item)
    return linhas


def indexar_videos(raiz: str) -> list[tuple[str, str]]:
    """Lista (nome_lower, caminho) de todos os videos abaixo de 'raiz'."""
    achados = []
    for pasta, _sub, arquivos in os.walk(raiz):
        for nome in arquivos:
            if nome.lower().endswith(EXTENSOES_VIDEO):
                achados.append((nome.lower(), os.path.join(pasta, nome)))
    return sorted(achados)


def achar_videos(indice: list[tuple[str, str]], video_id: str, camera: str) -> list[str]:
    """Retorna os caminhos de video cujo nome contem o video_id (e a camera, se dada)."""
    vid = video_id.lower()
    cam = camera.lower()
    return [
        caminho for nome, caminho in indice
        if vid in nome and (not cam or cam in nome)
    ]


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
    """Estatisticas de uma metrica para um grupo ('correto' ou 'incorreto')."""
    valores = [
        float(l[metrica]) for l in linhas
        if l["rotulo"] == grupo and l.get(metrica, "") != ""
    ]
    return {
        "n": len(valores),
        "media": _media(valores),
        "p10": _percentil(valores, 10),
        "mediana": _percentil(valores, 50),
        "p90": _percentil(valores, 90),
    }


def modo_listar(anotacoes: list[dict], indice: list[tuple[str, str]], camera: str) -> None:
    """Dry-run: mostra, por gravacao, o video casado e a contagem correto/incorreto."""
    por_video: dict[str, list[dict]] = {}
    for a in anotacoes:
        por_video.setdefault(a["video_id"], []).append(a)

    total_correto = sum(1 for a in anotacoes if a["correctness"] == 1)
    total_incorreto = len(anotacoes) - total_correto
    sem_video = 0
    ambiguos = 0

    print(f"{len(anotacoes)} repeticoes em {len(por_video)} gravacoes "
          f"(correto={total_correto}, incorreto={total_incorreto}).\n")

    for video_id in sorted(por_video):
        reps = por_video[video_id]
        c = sum(1 for r in reps if r["correctness"] == 1)
        i = len(reps) - c
        arquivos = achar_videos(indice, video_id, camera)
        if not arquivos:
            estado = "SEM VIDEO"
            sem_video += 1
        elif len(arquivos) > 1:
            estado = f"{len(arquivos)} arquivos (ambiguo)"
            ambiguos += 1
        else:
            estado = os.path.basename(arquivos[0])
        print(f"  {video_id}  reps={len(reps):2d} (ok={c},nok={i})  -> {estado}")

    print("\n===== RESUMO =====")
    print(f"  gravacoes sem video casado : {sem_video}")
    print(f"  gravacoes ambiguas (>1 video): {ambiguos}")
    if sem_video:
        print("\nAVISO: ha gravacoes sem video. Confira se descompactou o videos.zip")
        print("dentro de --raiz e se o nome do arquivo contem o video_id (ex.: PM_000).")
    if ambiguos:
        print("\nAVISO: ha gravacoes com mais de um video (as duas cameras). Passe")
        print("--camera Camera18 (ou Camera17) para fixar uma so.")


def processar(anotacoes: list[dict], indice: list[tuple[str, str]], camera: str,
              pular_frames: int, max_videos: int) -> list[dict]:
    """Extrai pose por gravacao e mede as metricas por repeticao (janela de frames)."""
    # Imports pesados so aqui: quem chega neste ponto vai de fato processar.
    from src.pose_extractor import extrair_pose
    from src.biomechanics import extrair_metricas

    por_video: dict[str, list[dict]] = {}
    for a in anotacoes:
        por_video.setdefault(a["video_id"], []).append(a)

    video_ids = sorted(por_video)
    if max_videos > 0:
        video_ids = video_ids[:max_videos]

    resultados: list[dict] = []
    for n, video_id in enumerate(video_ids, 1):
        arquivos = achar_videos(indice, video_id, camera)
        if not arquivos:
            print(f"[{n}/{len(video_ids)}] {video_id}: SEM VIDEO casado, pulando.")
            continue
        if len(arquivos) > 1:
            print(f"[{n}/{len(video_ids)}] {video_id}: {len(arquivos)} videos casaram; "
                  f"usando {os.path.basename(arquivos[0])}. Fixe --camera para evitar isso.")
        caminho = arquivos[0]

        try:
            # Extrai a pose do video INTEIRO uma vez; cada registro traz o indice
            # real do frame, entao conseguimos fatiar por repeticao depois.
            registros = extrair_pose(caminho, pular_frames=pular_frames)
        except Exception as e:  # noqa: BLE001 - queremos continuar o lote
            print(f"[{n}/{len(video_ids)}] ERRO em {os.path.basename(caminho)}: {e}")
            continue

        for rep in por_video[video_id]:
            janela = [r for r in registros
                      if rep["first_frame"] <= r["frame"] <= rep["last_frame"]]
            metricas = extrair_metricas(janela)
            linha = {
                "video_id": video_id,
                "repetition_number": rep["repetition_number"],
                "exercise_id": rep["exercise_id"],
                "person_id": rep["person_id"],
                "correctness": rep["correctness"],
                "rotulo": rotulo(rep["correctness"]),
                "first_frame": rep["first_frame"],
                "last_frame": rep["last_frame"],
                "frames_validos": metricas.get("frames_validos", 0),
            }
            for m in METRICAS:
                linha[m] = round(float(metricas.get(m, 0.0)), 4)
            resultados.append(linha)

        print(f"[{n}/{len(video_ids)}] {video_id}: {len(por_video[video_id])} repeticoes medidas "
              f"({os.path.basename(caminho)}).")

    return resultados


def comparar_e_sugerir(resultados: list[dict]) -> None:
    """Compara correto x incorreto por metrica e sugere limiares para config.py."""
    print("\n===== COMPARATIVO CORRETO x INCORRETO =====")
    for m in METRICAS:
        c = resumir_grupo(resultados, "correto", m)
        i = resumir_grupo(resultados, "incorreto", m)
        print(f"\n# {m}")
        print(f"  correto  : n={c['n']:3d}  media={c['media']:.3f}  mediana={c['mediana']:.3f}  "
              f"p10={c['p10']:.3f}  p90={c['p90']:.3f}")
        print(f"  incorreto: n={i['n']:3d}  media={i['media']:.3f}  mediana={i['mediana']:.3f}  "
              f"p10={i['p10']:.3f}  p90={i['p90']:.3f}")
        if c["n"] < 3:
            print("  -> poucas amostras corretas para sugerir; processe mais gravacoes.")
            continue
        if m == "velocidade":
            # Velocidade tem faixa (min e max): sugerimos o intervalo p10..p90 dos corretos.
            print(f"  -> sugestao (faixa dos corretos): velocidade_min={c['p10']:.3f}  "
                  f"velocidade_max={c['p90']:.3f}")
        else:
            # Demais metricas: corte no p90 dos corretos (a maioria das execucoes
            # corretas fica abaixo; acima disso tende a ser anomalia).
            print(f"  -> sugestao de limiar (p90 dos corretos): {c['p90']:.3f}")

    print("\nDica: focar 1 exercise_id por vez (--exercise) deixa a comparacao mais")
    print("limpa, pois cada exercicio tem uma faixa 'normal' diferente. Use as")
    print("sugestoes como ponto de partida e ajuste os valores em config.py.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibracao de limiares com o REHAB24-6")
    parser.add_argument("--raiz", required=True,
                        help="Pasta raiz do REHAB24-6 (com os videos e o Segmentation.csv)")
    parser.add_argument("--csv", default="",
                        help="Caminho do Segmentation.csv (padrao: <raiz>/Segmentation.csv)")
    parser.add_argument("--camera", default="",
                        help="Token do nome do arquivo para fixar uma camera (ex.: Camera18)")
    parser.add_argument("--exercise", type=int, default=None,
                        help="Filtra por exercise_id (1..6). Recomendado calibrar 1 por vez")
    parser.add_argument("--saida-csv", default="data/saida/calibracao.csv",
                        help="CSV de saida com as metricas por repeticao")
    parser.add_argument("--pular-frames", type=int, default=3,
                        help="Processa 1 a cada N frames (acelera em CPU). Padrao: 3")
    parser.add_argument("--max", type=int, default=0,
                        help="Limita o numero de gravacoes processadas (0 = todas)")
    parser.add_argument("--listar", action="store_true",
                        help="Dry-run: valida CSV + matching de video SEM processar")
    args = parser.parse_args()

    caminho_csv = args.csv or os.path.join(args.raiz, CSV_ANOTACAO)
    if not os.path.exists(caminho_csv):
        print(f"Nao encontrei o CSV de anotacao: {caminho_csv}")
        print("Baixe o Segmentation.csv do REHAB24-6 e coloque em --raiz (ou use --csv).")
        return

    anotacoes = carregar_anotacoes(caminho_csv, exercicio=args.exercise)
    if not anotacoes:
        alvo = f" para exercise_id={args.exercise}" if args.exercise is not None else ""
        print(f"Nenhuma repeticao encontrada no CSV{alvo}.")
        return

    indice = indexar_videos(args.raiz)

    if args.listar:
        modo_listar(anotacoes, indice, args.camera)
        return

    resultados = processar(anotacoes, indice, args.camera,
                           pular_frames=args.pular_frames, max_videos=args.max)
    if not resultados:
        print("\nNenhuma metrica extraida. Rode com --listar para conferir o matching de video.")
        return

    # Salva o CSV por repeticao.
    os.makedirs(os.path.dirname(args.saida_csv) or ".", exist_ok=True)
    campos = ["video_id", "repetition_number", "exercise_id", "person_id",
              "correctness", "rotulo", "first_frame", "last_frame", "frames_validos"] + METRICAS
    with open(args.saida_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(resultados)
    print(f"\nCSV salvo em: {args.saida_csv}")

    comparar_e_sugerir(resultados)


if __name__ == "__main__":
    main()
