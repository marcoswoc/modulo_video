"""
main.py
-------
Ponto de entrada por linha de comando (CLI) do modulo de video.

Exemplos de uso:

    # Processa um video e imprime o alerta JSON no terminal:
    python main.py --video data/entrada/sessao01.mp4 --patient-id video_001

    # Salva o alerta em JSON e gera um video com o esqueleto desenhado:
    python main.py --video data/entrada/sessao01.mp4 \
                   --patient-id video_001 \
                   --saida data/saida/video_001.json \
                   --anotado data/saida/video_001_anotado.mp4
"""

import argparse
import json

from src.pipeline import processar_video
from src.report import salvar_json, salvar_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Modulo de video - fisioterapia/marcha")
    parser.add_argument("--video", required=True, help="Caminho do video de entrada")
    parser.add_argument("--patient-id", default="video_001", help="Identificador do paciente/amostra")
    parser.add_argument("--saida", help="Caminho para salvar o alerta em JSON")
    parser.add_argument("--csv", help="Caminho para anexar o alerta em um CSV")
    parser.add_argument("--anotado", help="Caminho para salvar o video com esqueleto desenhado")
    parser.add_argument("--silencioso", action="store_true", help="Nao imprime os passos")
    args = parser.parse_args()

    alerta = processar_video(
        caminho_video=args.video,
        patient_id=args.patient_id,
        salvar_anotado=args.anotado,
        verbose=not args.silencioso,
    )

    print("\n===== ALERTA GERADO =====")
    print(json.dumps(alerta, ensure_ascii=False, indent=2))

    if args.saida:
        salvar_json(alerta, args.saida)
        print(f"\nJSON salvo em: {args.saida}")
    if args.csv:
        salvar_csv(alerta, args.csv)
        print(f"CSV atualizado em: {args.csv}")


if __name__ == "__main__":
    main()
