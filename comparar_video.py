"""
comparar_video.py
-----------------
Roda a analise em UM video e mostra o alerta ANTES x DEPOIS da calibracao,
lado a lado, para ver o efeito dos limiares no resultado final.

Como funciona
-------------
O video e processado UMA vez (pose + YOLOv8 -> metricas). Depois montamos dois
alertas sobre as MESMAS metricas:
  - ANTES:  limiares do config.py (os chutes);
  - DEPOIS: limiares calibrados, vindos de um JSON (gerado por
            `calibrar.py --salvar-limiares`).

Isso mantem tudo stateless: o config.py nunca muda; os limiares calibrados sao
apenas sobrepostos em memoria, so nesta execucao.

Uso
---
    # 1) gere os limiares calibrados (no calibrar.py):
    python calibrar.py --raiz REHAB24-6 --camera Camera17 --exercise 6 --salvar-limiares data/saida/limiares.json

    # 2) compare no video:
    python comparar_video.py --video data/entrada/video.mp4 --limiares data/saida/limiares.json
"""

from __future__ import annotations

import argparse
import json

import config
from src.pipeline import extrair_metricas_video, alerta_de_metricas


def _resumo(alerta: dict) -> str:
    return f"score={alerta['score_risco']} nivel={alerta['nivel_risco']}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compara o alerta antes x depois da calibracao num video")
    parser.add_argument("--video", required=True, help="Caminho do video de entrada")
    parser.add_argument("--patient-id", default="video_001", help="Identificador do paciente/amostra")
    parser.add_argument("--limiares", default="data/saida/limiares.json",
                        help="JSON com os limiares calibrados (de calibrar.py --salvar-limiares)")
    parser.add_argument("--sem-objetos", action="store_true",
                        help="Desativa a deteccao YOLOv8 (util em maquina fraca)")
    parser.add_argument("--anotado", help="Caminho para salvar o video com esqueleto desenhado")
    parser.add_argument("--silencioso", action="store_true", help="Nao imprime os passos")
    args = parser.parse_args()

    # Carrega os limiares calibrados e sobrepoe aos do config (so em memoria).
    try:
        with open(args.limiares, encoding="utf-8") as f:
            calibrados = json.load(f)
    except FileNotFoundError:
        print(f"Nao encontrei o JSON de limiares: {args.limiares}")
        print("Gere-o antes com: calibrar.py ... --salvar-limiares data/saida/limiares.json")
        return
    limiares_depois = {**config.LIMIARES, **calibrados}

    # Processa o video UMA vez -> metricas.
    metricas = extrair_metricas_video(
        args.video, salvar_anotado=args.anotado,
        usar_objetos=not args.sem_objetos, verbose=not args.silencioso,
    )

    # Monta os dois alertas sobre as mesmas metricas.
    alerta_antes = alerta_de_metricas(args.patient_id, metricas, None)             # chutes (config)
    alerta_depois = alerta_de_metricas(args.patient_id, metricas, limiares_depois)  # calibrado

    print("\n===== LIMIARES CALIBRADOS APLICADOS =====")
    for k, v in calibrados.items():
        print(f"  {k}: config={config.LIMIARES.get(k)}  ->  calibrado={v}")

    print("\n===== ALERTA ANTES (limiares do config / chute) =====")
    print(json.dumps(alerta_antes, ensure_ascii=False, indent=2))

    print("\n===== ALERTA DEPOIS (limiares calibrados) =====")
    print(json.dumps(alerta_depois, ensure_ascii=False, indent=2))

    print("\n===== RESUMO =====")
    print(f"  ANTES : {_resumo(alerta_antes)}")
    print(f"  DEPOIS: {_resumo(alerta_depois)}")
    if alerta_antes["descricao"] != alerta_depois["descricao"]:
        print("  As anomalias detectadas mudaram entre os dois conjuntos de limiares.")
    else:
        print("  As anomalias detectadas foram as mesmas nos dois conjuntos.")


if __name__ == "__main__":
    main()
