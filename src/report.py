"""
report.py
---------
ETAPA 5 do pipeline: monta o ALERTA no formato padronizado do grupo.

Esta eh a "saida oficial" do modulo de video. O schema segue exatamente o
combinado entre os tres modulos (video / audio / clinico) para que a etapa
final de FUSAO consiga juntar tudo.
"""

from __future__ import annotations

import csv
import json


def montar_alerta(
    patient_id: str,
    anomalias: list[dict],
    score: float,
    nivel: str,
    recomendacao: str,
) -> dict:
    """Constroi o dicionario de alerta no formato padrao."""
    if anomalias:
        descricao = " ".join(a["descricao"] for a in anomalias)
    else:
        descricao = "Nenhum desvio significativo de postura ou marcha."

    return {
        "patient_id": patient_id,
        "modulo": "video_fisioterapia",
        "tipo_anomalia": "movimento",
        "score_risco": score,
        "nivel_risco": nivel,
        "descricao": descricao,
        "recomendacao": recomendacao,
    }


def salvar_json(alerta: dict, caminho: str) -> None:
    """Grava o alerta em arquivo JSON (UTF-8, legivel)."""
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(alerta, f, ensure_ascii=False, indent=2)


def salvar_csv(alerta: dict, caminho: str) -> None:
    """Grava (ou anexa) o alerta em um CSV, uma linha por paciente."""
    import os
    escrever_cabecalho = not os.path.exists(caminho)
    with open(caminho, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(alerta.keys()))
        if escrever_cabecalho:
            writer.writeheader()
        writer.writerow(alerta)
