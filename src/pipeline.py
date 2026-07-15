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

from config import LIMIARES
from src.pose_extractor import extrair_pose
from src.object_detector import detectar_objetos, extrair_metricas_objetos
from src.biomechanics import extrair_metricas
from src.anomaly_detector import detectar_anomalias
from src.risk_scoring import calcular_score, classificar_nivel, recomendar
from src.report import montar_alerta


def extrair_metricas_video(
    caminho_video: str,
    salvar_anotado: str | None = None,
    usar_objetos: bool = True,
    verbose: bool = True,
) -> dict:
    """
    Etapas 1, 1b e 2: video -> metricas (biomecanicas + eventos do YOLOv8).

    So depende do VIDEO, nao dos limiares. Isso permite extrair as metricas uma
    vez e depois aplicar diferentes conjuntos de limiares (ex.: comparar chute x
    calibrado) sem reprocessar o video.
    """
    # (1) Video -> pontos-chave (postura / MediaPipe)
    if verbose:
        print(f"[1/5] Extraindo pose de: {caminho_video}")
    registros = extrair_pose(caminho_video, salvar_anotado=salvar_anotado)
    if verbose:
        print(f"      {len(registros)} frames com pessoa detectada.")

    # (2) Pontos-chave -> metricas biomecanicas
    if verbose:
        print("[2/5] Calculando metricas biomecanicas...")
    metricas = extrair_metricas(registros)

    # (1b + 2b) Video -> objetos/pessoas (YOLOv8) -> metricas de eventos
    if usar_objetos:
        if verbose:
            print("[1b] Detectando objetos/pessoas com YOLOv8...")
        registros_obj = detectar_objetos(caminho_video, verbose=verbose)
        metricas_obj = extrair_metricas_objetos(registros_obj, LIMIARES["queda_razao_wh"])
        metricas.update(metricas_obj)

    if verbose:
        for k, v in metricas.items():
            print(f"      - {k}: {v}")
    return metricas


def alerta_de_metricas(
    patient_id: str,
    metricas: dict,
    limiares: dict | None = None,
) -> dict:
    """
    Etapas 3, 4 e 5: metricas + limiares -> alerta padronizado.

    Se 'limiares' for None, usa os do config.py (os chutes). Passando outro
    dicionario, aplica limiares alternativos (ex.: calibrados) as MESMAS metricas.
    """
    anomalias = detectar_anomalias(metricas, limiares)
    score = calcular_score(anomalias)
    nivel = classificar_nivel(score)
    recomendacao = recomendar(nivel, anomalias)
    return montar_alerta(patient_id, anomalias, score, nivel, recomendacao)


def processar_video(
    caminho_video: str,
    patient_id: str,
    salvar_anotado: str | None = None,
    usar_objetos: bool = True,
    verbose: bool = True,
    limiares: dict | None = None,
) -> dict:
    """
    Executa o pipeline completo para UM video e devolve o alerta padronizado.

    Se usar_objetos=True, roda tambem a deteccao com YOLOv8 (etapa 1b) e
    junta as metricas de eventos (queda, ausencia, contagem) as biomecanicas.
    'limiares' permite sobrepor os do config.py (None = usa os chutes).
    """
    metricas = extrair_metricas_video(
        caminho_video, salvar_anotado=salvar_anotado,
        usar_objetos=usar_objetos, verbose=verbose,
    )
    if verbose:
        print("[3/5] Aplicando regras de deteccao de anomalias...")
        print("[4/5] Calculando score e nivel de risco...")
        print("[5/5] Montando alerta padronizado.")
    return alerta_de_metricas(patient_id, metricas, limiares)
