"""
config.py
---------
Ponto unico de configuracao do modulo de video.

Aqui ficam TODOS os "numeros magicos" (limiares clinicos, pesos, faixas de
risco). Manter isso separado do codigo facilita ajustar o comportamento do
detector sem mexer na logica -- e deixa claro para a banca quais criterios
voce adotou.
"""

# ---------------------------------------------------------------------------
# 1) Indices dos pontos-chave (landmarks) do MediaPipe Pose.
#    O MediaPipe devolve 33 pontos do corpo. Damos nomes aos que usamos.
#    Referencia: https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
# ---------------------------------------------------------------------------
LANDMARKS = {
    "nariz": 0,
    "ombro_esq": 11, "ombro_dir": 12,
    "cotovelo_esq": 13, "cotovelo_dir": 14,
    "punho_esq": 15, "punho_dir": 16,
    "quadril_esq": 23, "quadril_dir": 24,
    "joelho_esq": 25, "joelho_dir": 26,
    "tornozelo_esq": 27, "tornozelo_dir": 28,
}

# ---------------------------------------------------------------------------
# 2) Limiares clinicos (ajuste conforme o dataset / validacao).
#    Cada limiar vira uma "regra" no anomaly_detector.
# ---------------------------------------------------------------------------
LIMIARES = {
    # Inclinacao do tronco em relacao a vertical (graus).
    # Acima disso consideramos "inclinacao excessiva".
    "inclinacao_tronco_graus": 15.0,

    # Indice de simetria de marcha (0 = perfeitamente simetrico).
    # Diferenca relativa entre lado esquerdo e direito acima disso = assimetria.
    "assimetria_marcha": 0.20,   # 20%

    # Estabilidade: desvio-padrao da oscilacao lateral do quadril (coord. normalizada).
    # Quanto maior, mais o paciente "balanca" -> menos estavel.
    "instabilidade_lateral": 0.04,

    # Velocidade de marcha esperada (unidades normalizadas/seg).
    # Fora dessa faixa consideramos "velocidade fora do padrao".
    "velocidade_min": 0.02,
    "velocidade_max": 0.35,
}

# ---------------------------------------------------------------------------
# 3) Peso de cada anomalia no score final (0 a 1).
#    O score de risco eh uma media ponderada das anomalias detectadas.
# ---------------------------------------------------------------------------
PESOS_ANOMALIA = {
    "inclinacao_tronco": 0.30,
    "assimetria_marcha": 0.30,
    "instabilidade": 0.25,
    "velocidade_anormal": 0.15,
}

# ---------------------------------------------------------------------------
# 4) Faixas de nivel de risco (combinar com os outros modulos do grupo!).
# ---------------------------------------------------------------------------
FAIXAS_RISCO = {
    "baixo": (0.0, 0.4),      # score < 0.4
    "moderado": (0.4, 0.7),   # 0.4 <= score < 0.7
    "alto": (0.7, 1.01),      # score >= 0.7
}

# Confianca minima do landmark para considerarmos o ponto valido.
CONFIANCA_MINIMA = 0.5
