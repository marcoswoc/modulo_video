"""
biomechanics.py
---------------
ETAPA 2 do pipeline: PONTOS-CHAVE -> METRICAS BIOMECANICAS.

A partir dos landmarks de cada frame, calculamos grandezas que fazem sentido
clinicamente:
  - inclinacao do tronco (graus)
  - angulos das articulacoes (ex.: joelho)
  - simetria de marcha (esquerda x direita)
  - velocidade de deslocamento
  - estabilidade (oscilacao lateral)

Cada funcao recebe a lista de 'registros' produzida pelo pose_extractor e
devolve numeros agregados (media, amplitude, desvio-padrao...).
"""

from __future__ import annotations

import math
import numpy as np

from config import CONFIANCA_MINIMA


# ---------------------------------------------------------------------------
# Funcoes auxiliares de geometria
# ---------------------------------------------------------------------------
def _ponto_valido(landmark) -> bool:
    """Um ponto so eh confiavel se a 'visibility' passar do minimo."""
    return landmark is not None and landmark[2] >= CONFIANCA_MINIMA


def _ponto_medio(a, b):
    """Ponto medio entre dois landmarks (usa so x, y)."""
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def calcular_angulo(a, b, c) -> float:
    """
    Angulo (em graus) formado no vertice B pelos segmentos B->A e B->C.

    Usado, por exemplo, para o angulo do joelho (quadril-joelho-tornozelo).
    """
    a = np.array(a[:2]); b = np.array(b[:2]); c = np.array(c[:2])
    ba = a - b
    bc = c - b
    cos = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-9)
    cos = np.clip(cos, -1.0, 1.0)
    return math.degrees(math.acos(cos))


def inclinacao_tronco(a_quadril_medio, a_ombro_medio) -> float:
    """
    Angulo do tronco em relacao a vertical (0 = ereto).

    Vetor tronco = ombro_medio - quadril_medio; comparamos com o eixo vertical.
    """
    dx = a_ombro_medio[0] - a_quadril_medio[0]
    dy = a_ombro_medio[1] - a_quadril_medio[1]
    # atan2(dx, dy): quanto o tronco desvia da vertical.
    return abs(math.degrees(math.atan2(dx, -dy)))


# ---------------------------------------------------------------------------
# Metricas agregadas (percorrem o video inteiro)
# ---------------------------------------------------------------------------
def metrica_inclinacao_tronco(registros: list[dict]) -> float:
    """Inclinacao MEDIA do tronco ao longo do video (graus)."""
    valores = []
    for r in registros:
        lm = r["landmarks"]
        oe, od = lm["ombro_esq"], lm["ombro_dir"]
        qe, qd = lm["quadril_esq"], lm["quadril_dir"]
        if all(_ponto_valido(p) for p in (oe, od, qe, qd)):
            ombro_m = _ponto_medio(oe, od)
            quadril_m = _ponto_medio(qe, qd)
            valores.append(inclinacao_tronco(quadril_m, ombro_m))
    return float(np.mean(valores)) if valores else 0.0


def _serie_angulo_joelho(registros: list[dict], lado: str) -> list[float]:
    """Serie temporal do angulo do joelho de um lado ('esq' ou 'dir')."""
    serie = []
    for r in registros:
        lm = r["landmarks"]
        q, j, t = lm[f"quadril_{lado}"], lm[f"joelho_{lado}"], lm[f"tornozelo_{lado}"]
        if all(_ponto_valido(p) for p in (q, j, t)):
            serie.append(calcular_angulo(q, j, t))
    return serie


def metrica_assimetria_marcha(registros: list[dict]) -> float:
    """
    Indice de assimetria entre pernas (0 = simetrico).

    Comparamos a AMPLITUDE de movimento do joelho esquerdo x direito.
    Amplitude = max - min do angulo ao longo do video.
    """
    esq = _serie_angulo_joelho(registros, "esq")
    dir_ = _serie_angulo_joelho(registros, "dir")
    if not esq or not dir_:
        return 0.0

    amp_esq = max(esq) - min(esq)
    amp_dir = max(dir_) - min(dir_)
    denom = max(amp_esq, amp_dir) + 1e-9
    return abs(amp_esq - amp_dir) / denom


def metrica_estabilidade(registros: list[dict]) -> float:
    """
    Instabilidade = desvio-padrao da posicao lateral (x) do quadril medio.

    Muito balanco lateral -> valor alto -> menos estavel.
    """
    xs = []
    for r in registros:
        lm = r["landmarks"]
        qe, qd = lm["quadril_esq"], lm["quadril_dir"]
        if _ponto_valido(qe) and _ponto_valido(qd):
            xs.append(_ponto_medio(qe, qd)[0])
    return float(np.std(xs)) if len(xs) > 1 else 0.0


def metrica_velocidade(registros: list[dict]) -> float:
    """
    Velocidade media de deslocamento do quadril medio (unid. normalizada/seg).

    Distancia total percorrida dividida pela duracao do video.
    """
    pontos = []
    tempos = []
    for r in registros:
        lm = r["landmarks"]
        qe, qd = lm["quadril_esq"], lm["quadril_dir"]
        if _ponto_valido(qe) and _ponto_valido(qd):
            pontos.append(_ponto_medio(qe, qd))
            tempos.append(r["timestamp"])

    if len(pontos) < 2:
        return 0.0

    distancia = 0.0
    for i in range(1, len(pontos)):
        dx = pontos[i][0] - pontos[i - 1][0]
        dy = pontos[i][1] - pontos[i - 1][1]
        distancia += math.hypot(dx, dy)

    duracao = tempos[-1] - tempos[0]
    return distancia / duracao if duracao > 0 else 0.0


def extrair_metricas(registros: list[dict]) -> dict:
    """
    Facade: calcula TODAS as metricas de uma vez e devolve um dicionario.
    Eh o que o pipeline consome.
    """
    return {
        "inclinacao_tronco_graus": metrica_inclinacao_tronco(registros),
        "assimetria_marcha": metrica_assimetria_marcha(registros),
        "instabilidade_lateral": metrica_estabilidade(registros),
        "velocidade": metrica_velocidade(registros),
        "frames_validos": len(registros),
    }
