"""
avaliar.py
----------
Compara o desempenho dos limiares ANTES e DEPOIS da calibracao, usando os dados
rotulados gerados pelo calibrar.py (data/saida/calibracao.csv).

A ideia: cada linha do CSV e uma repeticao com rotulo correto/incorreto e as
metricas medidas. Para cada metrica, aplicamos dois limiares:
  - ANTES:  o valor atual em config.py (chute inicial);
  - DEPOIS: o valor calibrado a partir dos dados (p90 das execucoes corretas;
            para velocidade, a faixa p10..p90 das corretas).

E medimos, para cada um:
  - sensibilidade: % das execucoes INCORRETAS que o limiar pega (quanto maior, melhor);
  - falso positivo: % das execucoes CORRETAS que o limiar dispara por engano (menor, melhor).

Assim da para mostrar, com numeros, o ganho da calibracao. Nao processa video:
so le o CSV e o config, entao roda em qualquer lugar (sem cv2/mediapipe).

Uso
---
    python avaliar.py                                  # usa data/saida/calibracao.csv
    python avaliar.py --csv data/saida/calibracao.csv --exercise 6
"""

from __future__ import annotations

import argparse
import csv

from config import LIMIARES

# Metricas "de teto": anomalia quando o valor PASSA do limiar.
METRICAS_TETO = ["inclinacao_tronco_graus", "assimetria_marcha", "instabilidade_lateral"]


def _percentil(valores: list[float], p: float) -> float:
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


def carregar(caminho_csv: str, exercicio: int | None) -> list[dict]:
    linhas = []
    with open(caminho_csv, newline="", encoding="utf-8") as f:
        for reg in csv.DictReader(f):
            if exercicio is not None and int(reg["exercise_id"]) != exercicio:
                continue
            linhas.append(reg)
    return linhas


def _taxas_teto(linhas: list[dict], metrica: str, limiar: float) -> tuple[int, int, int, int]:
    """Conta (pega_incorreto, n_incorreto, dispara_correto, n_correto) para limiar de teto."""
    pega_inc = n_inc = disp_cor = n_cor = 0
    for l in linhas:
        v = float(l[metrica])
        anomalia = v > limiar
        if int(l["correctness"]) == 0:   # execucao incorreta = deveria virar anomalia
            n_inc += 1
            pega_inc += anomalia
        else:
            n_cor += 1
            disp_cor += anomalia
    return pega_inc, n_inc, disp_cor, n_cor


def _taxas_faixa(linhas: list[dict], metrica: str, lo: float, hi: float) -> tuple[int, int, int, int]:
    """Idem para metrica de faixa: anomalia quando o valor cai FORA de [lo, hi]."""
    pega_inc = n_inc = disp_cor = n_cor = 0
    for l in linhas:
        v = float(l[metrica])
        anomalia = v < lo or v > hi
        if int(l["correctness"]) == 0:
            n_inc += 1
            pega_inc += anomalia
        else:
            n_cor += 1
            disp_cor += anomalia
    return pega_inc, n_inc, disp_cor, n_cor


def _pct(parte: int, total: int) -> str:
    return f"{(100.0 * parte / total):.0f}% ({parte}/{total})" if total else "n/d (0)"


def _imprimir_bloco(rotulo: str, limiar_desc: str, pega_inc, n_inc, disp_cor, n_cor) -> None:
    print(f"  limiar {rotulo} ({limiar_desc})")
    print(f"    pega incorretos (sensibilidade): {_pct(pega_inc, n_inc)}")
    print(f"    dispara em corretos (falso pos.): {_pct(disp_cor, n_cor)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compara limiares antes x depois da calibracao")
    parser.add_argument("--csv", default="data/saida/calibracao.csv",
                        help="CSV gerado pelo calibrar.py")
    parser.add_argument("--exercise", type=int, default=None,
                        help="Filtra por exercise_id (recomendado, o mesmo usado na calibracao)")
    args = parser.parse_args()

    try:
        linhas = carregar(args.csv, args.exercise)
    except FileNotFoundError:
        print(f"Nao encontrei o CSV: {args.csv}")
        print("Rode antes o calibrar.py para gera-lo (ele salva em data/saida/calibracao.csv).")
        return
    if not linhas:
        print("Nenhuma linha no CSV (confira o --exercise).")
        return

    corretas = [l for l in linhas if int(l["correctness"]) == 1]
    incorretas = [l for l in linhas if int(l["correctness"]) == 0]
    print(f"Avaliando {len(linhas)} repeticoes "
          f"(corretas={len(corretas)}, incorretas={len(incorretas)})"
          + (f" do exercicio {args.exercise}" if args.exercise is not None else "") + ".\n")

    if not corretas or not incorretas:
        print("Preciso dos DOIS grupos (correto e incorreto) para comparar. Processe mais dados.")
        return

    # Metricas de teto: ANTES = config, DEPOIS = p90 das corretas.
    for m in METRICAS_TETO:
        antes = float(LIMIARES[m])
        vals_cor = [float(l[m]) for l in corretas]
        depois = _percentil(vals_cor, 90)
        print(f"# {m}")
        _imprimir_bloco("ANTES", f"config={antes:.3f}", *_taxas_teto(linhas, m, antes))
        _imprimir_bloco("DEPOIS", f"calibrado={depois:.3f}", *_taxas_teto(linhas, m, depois))
        print()

    # Velocidade: faixa. ANTES = config [min, max], DEPOIS = [p10, p90] das corretas.
    m = "velocidade"
    antes_lo, antes_hi = float(LIMIARES["velocidade_min"]), float(LIMIARES["velocidade_max"])
    vals_cor = [float(l[m]) for l in corretas]
    depois_lo, depois_hi = _percentil(vals_cor, 10), _percentil(vals_cor, 90)
    print(f"# {m}")
    _imprimir_bloco("ANTES", f"config=[{antes_lo:.3f}, {antes_hi:.3f}]",
                    *_taxas_faixa(linhas, m, antes_lo, antes_hi))
    _imprimir_bloco("DEPOIS", f"calibrado=[{depois_lo:.3f}, {depois_hi:.3f}]",
                    *_taxas_faixa(linhas, m, depois_lo, depois_hi))
    print()

    print("Leitura: um bom limiar tem sensibilidade alta (pega os incorretos) e")
    print("falso positivo baixo (nao acusa os corretos). Compare ANTES x DEPOIS.")


if __name__ == "__main__":
    main()
