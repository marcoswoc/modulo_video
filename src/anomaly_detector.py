"""
anomaly_detector.py
--------------------
ETAPA 3 do pipeline: METRICAS -> ANOMALIAS (desvios).

Aplica REGRAS CLINICAS SIMPLES (comparacao com os limiares do config) para
transformar numeros em achados interpretaveis. Cada anomalia detectada vem
com:
  - chave    : identificador usado nos pesos (config.PESOS_ANOMALIA)
  - descricao: texto legivel para o relatorio
  - gravidade: 0 a 1 (o quanto o valor passou do limiar)

OBS: aqui usamos regras (facil de explicar para a banca). Um proximo passo
opcional seria trocar/complementar por um modelo nao supervisionado
(ex.: Isolation Forest) sobre as metricas -- deixamos um TODO no fim.
"""

from __future__ import annotations

from config import LIMIARES


def _gravidade(valor: float, limiar: float, teto: float) -> float:
    """
    Normaliza o quanto 'valor' ultrapassou 'limiar' em uma escala 0..1.
    'teto' eh o valor a partir do qual consideramos gravidade maxima (1.0).
    """
    if valor <= limiar:
        return 0.0
    return min((valor - limiar) / (teto - limiar + 1e-9), 1.0)


def detectar_anomalias(metricas: dict) -> list[dict]:
    """Recebe as metricas biomecanicas e devolve a lista de anomalias."""
    anomalias: list[dict] = []

    # --- Regra 1: inclinacao excessiva do tronco ---------------------------
    inc = metricas["inclinacao_tronco_graus"]
    lim = LIMIARES["inclinacao_tronco_graus"]
    if inc > lim:
        anomalias.append({
            "chave": "inclinacao_tronco",
            "descricao": f"Inclinacao excessiva do tronco ({inc:.1f} graus).",
            "gravidade": _gravidade(inc, lim, teto=lim * 2),
        })

    # --- Regra 2: assimetria de marcha -------------------------------------
    ass = metricas["assimetria_marcha"]
    lim = LIMIARES["assimetria_marcha"]
    if ass > lim:
        anomalias.append({
            "chave": "assimetria_marcha",
            "descricao": f"Assimetria de passada entre as pernas ({ass*100:.0f}%).",
            "gravidade": _gravidade(ass, lim, teto=lim * 2.5),
        })

    # --- Regra 3: instabilidade / perda de equilibrio ----------------------
    inst = metricas["instabilidade_lateral"]
    lim = LIMIARES["instabilidade_lateral"]
    if inst > lim:
        anomalias.append({
            "chave": "instabilidade",
            "descricao": "Oscilacao lateral elevada (perda de estabilidade).",
            "gravidade": _gravidade(inst, lim, teto=lim * 2.5),
        })

    # --- Regra 4: velocidade fora do padrao --------------------------------
    vel = metricas["velocidade"]
    vmin, vmax = LIMIARES["velocidade_min"], LIMIARES["velocidade_max"]
    if vel < vmin or vel > vmax:
        sentido = "abaixo" if vel < vmin else "acima"
        anomalias.append({
            "chave": "velocidade_anormal",
            "descricao": f"Velocidade de marcha {sentido} do esperado ({vel:.3f}).",
            # Gravidade fixa moderada; refine com dados reais.
            "gravidade": 0.6,
        })

    # TODO (evolucao): treinar um Isolation Forest com as metricas de varios
    # pacientes "normais" e usar o score de anomalia como 5a regra/validacao.
    return anomalias
