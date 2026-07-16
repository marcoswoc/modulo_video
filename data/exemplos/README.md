# Exemplos de saída (resultados reais)

Arquivos gerados a partir do dataset **REHAB24-6**, exercício 6 (agachamento),
câmera Camera17, `--pular-frames 5`. Servem para ver um resultado sem precisar
baixar o dataset nem rodar o pipeline.

| Arquivo | O que é |
|---|---|
| `calibracao_agachamento.csv` | Métricas por repetição (195 repetições: 134 corretas, 61 incorretas), com o rótulo correto/incorreto. Saída do `calibrar.py`. |
| `limiares_agachamento.json` | Limiares calibrados a partir das execuções corretas (p90; faixa p10..p90 para velocidade). Saída de `calibrar.py --salvar-limiares`. |
| `alerta_agachamento.json` | Alerta final (schema padrão) de um vídeo de agachamento, com os limiares do `config.py`. |

## Calibração: correto x incorreto (9 gravações, 195 repetições)

| Métrica | Correto (média / p90) | Incorreto (média / p90) |
|---|---|---|
| inclinação tronco (graus) | 4.04 / 9.08 | 6.09 / 13.81 |
| assimetria de marcha | 0.36 / 0.87 | 0.28 / 0.67 |
| instabilidade lateral | 0.006 / 0.014 | 0.006 / 0.011 |
| velocidade | 0.084 / 0.123 | 0.110 / 0.147 |

## Antes x depois dos limiares (nos dados rotulados)

Sensibilidade = % das execuções incorretas que o limiar pega. Falso positivo =
% das corretas que ele acusa por engano.

| Métrica | Limiar ANTES (config) | sens. / falso pos. | Limiar DEPOIS (calibrado) | sens. / falso pos. |
|---|---|---|---|---|
| inclinação tronco | 15.0 | 5% / 1% | 9.08 | 25% / 10% |
| assimetria marcha | 0.20 | 43% / 63% | 0.87 | 0% / 10% |
| instabilidade lateral | 0.04 | 0% / 0% | 0.014 | 2% / 10% |
| velocidade | [0.02, 0.35] | 0% / 0% | [0.039, 0.123] | 31% / 21% |

## Leitura dos resultados (honesta)

1. **Os chutes do `config.py` estavam fora de escala.** A instabilidade lateral
   real fica em ~0.005 a 0.014, mas o limiar era 0.04 (nunca disparava); a faixa
   de velocidade era larga demais. A calibração corrigiu essa escala.
2. **Para agachamento, inclinação de tronco e velocidade são as métricas que
   separam melhor** correto de incorreto (sensibilidade sobe de ~0 a 5% para
   25 a 31%, com falso positivo controlado).
3. **Assimetria de marcha e instabilidade lateral quase não separam o
   agachamento**, e isso é esperado: assimetria é uma métrica de *marcha* (compara
   perna esquerda x direita ao caminhar), e o agachamento é um movimento
   simétrico e bilateral, com pouca oscilação lateral. A calibração deixa esses
   dois limiares mais conservadores (menos falso positivo), mas o sinal e fraco.

Conclusão: a calibração serve para (a) ajustar a escala dos limiares com dados
reais e (b) mostrar, com números, quais métricas são informativas para cada tipo
de exercício. Para marcha (não coberta pelo REHAB24-6), a assimetria seria a
métrica relevante.

## Antes x depois num vídeo (gravação PM_029)

Mesmo vídeo, mesmos dados de pose, mudando só os limiares (o `comparar_video.py`
processa o vídeo uma vez e monta os dois alertas):

- **ANTES (limiares do `config.py`)**: `score_risco = 0.0`, "Nenhum desvio
  significativo". Com os chutes fora de escala, a sessão passa despercebida.
- **DEPOIS (limiares calibrados)**: `score_risco = 0.13`, "Oscilacao lateral
  elevada (perda de estabilidade)". Com a escala corrigida, o desvio aparece.

Ou seja, a calibração muda o resultado da análise, não só os números dos limiares.

## Como reproduzir

```bash
python calibrar.py --raiz REHAB24-6 --camera Camera17 --exercise 6 --pular-frames 5 --salvar-limiares data/saida/limiares.json
python avaliar.py --exercise 6
python comparar_video.py --video REHAB24-6/videos/Ex6/PM_029-Camera17-30fps.mp4 --limiares data/saida/limiares.json --sem-objetos
```
