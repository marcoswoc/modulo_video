"""
risk_scoring.py
---------------
ETAPA 4 do pipeline: ANOMALIAS -> SCORE E NIVEL DE RISCO.

Combina as anomalias detectadas em um unico 'score_risco' (0 a 1) usando os
pesos do config, e traduz esse numero para 'nivel_risco'
(baixo / moderado / alto).

Este eh o ponto de contrato com os outros modulos do grupo: todos devem
produzir score 0..1 + nivel na MESMA escala (ver config.FAIXAS_RISCO).
"""

from __future__ import annotations

from config import PESOS_ANOMALIA, FAIXAS_RISCO


def calcular_score(anomalias: list[dict]) -> float:
    """
    Score de risco = soma ponderada (peso * gravidade) das anomalias.

    Cada anomalia contribui com peso_da_anomalia * gravidade. O resultado eh
    limitado a 1.0. Se nenhuma anomalia -> 0.0.
    """
    score = 0.0
    for a in anomalias:
        peso = PESOS_ANOMALIA.get(a["chave"], 0.0)
        score += peso * a["gravidade"]
    return round(min(score, 1.0), 2)


def classificar_nivel(score: float) -> str:
    """Traduz o score numerico para baixo / moderado / alto."""
    for nivel, (minimo, maximo) in FAIXAS_RISCO.items():
        if minimo <= score < maximo:
            return nivel
    return "alto"  # seguranca: score >= teto -> alto


def recomendar(nivel: str, anomalias: list[dict]) -> str:
    """Gera uma recomendacao textual simples a partir do nivel de risco."""
    if not anomalias:
        return "Nenhum desvio relevante detectado. Manter acompanhamento de rotina."
    if nivel == "alto":
        return "Revisar imediatamente o exercicio de fisioterapia e acionar o responsavel."
    if nivel == "moderado":
        return "Revisar o exercicio de fisioterapia e reavaliar a evolucao do paciente."
    return "Manter o plano atual e monitorar nas proximas sessoes."
