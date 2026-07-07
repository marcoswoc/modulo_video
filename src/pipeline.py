"""
pipeline.py
-----------
ORQUESTRADOR: liga as 5 etapas em sequencia.

    video --(1)--> keypoints --(2)--> metricas --(3)--> anomalias
          --(4)--> score/nivel --(5)--> alerta padronizado (dict)

Este arquivo nao contem "logica" propria: ele so chama, na ordem certa, as
funcoes de cada modulo. Isso deixa o fluxo facil de ler e de testar.
"""

from __future__ import annotations

from src.pose_extractor import extrair_pose
from src.biomechanics import extrair_metricas
from src.anomaly_detector import detectar_anomalias
from src.risk_scoring import calcular_score, classificar_nivel, recomendar
from src.report import montar_alerta


def processar_video(
    caminho_video: str,
    patient_id: str,
    salvar_anotado: str | None = None,
    verbose: bool = True,
) -> dict:
    """
    Executa o pipeline completo para UM video e devolve o alerta padronizado.
    """
    # (1) Video -> pontos-chave
    if verbose:
        print(f"[1/5] Extraindo pose de: {caminho_video}")
    registros = extrair_pose(caminho_video, salvar_anotado=salvar_anotado)
    if verbose:
        print(f"      {len(registros)} frames com pessoa detectada.")

    # (2) Pontos-chave -> metricas biomecanicas
    if verbose:
        print("[2/5] Calculando metricas biomecanicas...")
    metricas = extrair_metricas(registros)
    if verbose:
        for k, v in metricas.items():
            print(f"      - {k}: {v}")

    # (3) Metricas -> anomalias
    if verbose:
        print("[3/5] Aplicando regras de deteccao de anomalias...")
    anomalias = detectar_anomalias(metricas)

    # (4) Anomalias -> score e nivel
    if verbose:
        print("[4/5] Calculando score e nivel de risco...")
    score = calcular_score(anomalias)
    nivel = classificar_nivel(score)
    recomendacao = recomendar(nivel, anomalias)

    # (5) Monta o alerta padronizado
    if verbose:
        print("[5/5] Montando alerta padronizado.")
    alerta = montar_alerta(patient_id, anomalias, score, nivel, recomendacao)

    return alerta
