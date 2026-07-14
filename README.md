# Módulo de Vídeo — Fisioterapia / Postura / Marcha

Parte do Tech Challenge (Fase 4) responsável por **analisar vídeos de
fisioterapia**, estimar a postura do paciente e detectar desvios de movimento
(inclinação de tronco, assimetria de marcha, instabilidade, velocidade fora do
padrão), gerando um **alerta padronizado** para a etapa de fusão multimodal.

## Fluxo (pipeline)

```
vídeo ─┬─(1)  pose_extractor  ──▶ keypoints (postura, MediaPipe/OpenPose)
       └─(1b) object_detector ──▶ pessoas/objetos (YOLOv8)
                      │
                      ▼
      ──(2) biomechanics + métricas de eventos ──▶ métricas
      ──(3) anomaly_detector──▶ anomalias ──(4) risk_scoring──▶ score/nível
      ──(5) report──▶ alerta JSON/CSV
```

O módulo usa **dois modelos** de visão, como pede o desafio:
- **MediaPipe Pose** (equivalente prático ao **OpenPose**) para análise postural e de marcha.
- **YOLOv8** para detecção de pessoas/objetos e eventos de segurança: possível
  **queda**, **paciente ausente** do quadro e **contagem de pessoas**.

## Estrutura

| Arquivo | Responsabilidade |
|---|---|
| `config.py` | Limiares clínicos, pesos e faixas de risco (todos os "números mágicos") |
| `src/pose_extractor.py` | (1) Vídeo → pontos-chave do corpo (MediaPipe Pose) |
| `src/object_detector.py` | (1b) Vídeo → pessoas/objetos e eventos (YOLOv8): queda, ausência, contagem |
| `src/biomechanics.py` | (2) Pontos-chave → ângulos, simetria, velocidade, estabilidade |
| `src/anomaly_detector.py` | (3) Métricas → anomalias (regras clínicas) |
| `src/risk_scoring.py` | (4) Anomalias → score 0–1 e nível baixo/moderado/alto |
| `src/report.py` | (5) Monta o alerta no schema padrão e salva JSON/CSV |
| `src/pipeline.py` | Orquestra as 5 etapas |
| `main.py` | Linha de comando (CLI) |

## Como rodar

```bash
# 1) Crie um ambiente virtual (Python 3.10 ou 3.11 recomendado)
python -m venv .venv
.venv\Scripts\activate        # Windows

# 2) Instale as dependências
pip install -r requirements.txt

# 3) Coloque um vídeo em data/entrada/ e rode:
python main.py --video data/entrada/sessao01.mp4 --patient-id video_001 \
               --saida data/saida/video_001.json \
               --anotado data/saida/video_001_anotado.mp4

# Em máquina fraca, dá para desativar o YOLOv8 (roda só a postura):
python main.py --video data/entrada/sessao01.mp4 --sem-objetos
```

### Rodar no Google Colab (sem instalar nada localmente)

Abra o notebook **`colab_modulo_video.ipynb`** no Google Colab
([colab.research.google.com](https://colab.research.google.com) → *GitHub* →
cole a URL do repositório). Ele clona o projeto, instala as dependências,
recebe o upload de um vídeo, roda o pipeline e baixa o alerta JSON e o vídeo
anotado. Recomendado para máquinas sem GPU/processamento sobrando.

## Saída (schema combinado com o grupo)

```json
{
  "patient_id": "video_001",
  "modulo": "video_fisioterapia",
  "tipo_anomalia": "movimento",
  "score_risco": 0.72,
  "nivel_risco": "moderado",
  "descricao": "Assimetria de passada entre as pernas (28%). Inclinacao excessiva do tronco (19.4 graus).",
  "recomendacao": "Revisar o exercicio de fisioterapia e reavaliar a evolucao do paciente."
}
```

## Dataset

Este módulo processa **vídeo RGB** (via MediaPipe Pose), a mesma técnica vista
em aula. Por isso usamos o **[REHAB24-6](https://zenodo.org/records/13305826)**
(exercícios de reabilitação gravados em RGB por duas câmeras, publicado no Zenodo
sob licença CC-BY-NC, download livre e sem EULA). Cada repetição tem rótulo
binário de **execução correta (1) x incorreta (0)** no `Segmentation.csv`, o que
mapeia diretamente no conceito de anomalia da spec ("movimentos fora do padrão
esperado"). O `calibrar.py` usa esse rótulo para ajustar os limiares em `config.py`.

> Datasets descartados e o porquê:
> - *Multi-Gait-Posture* (PhysioNet): apenas profundidade (depth) e esqueleto
>   (CSV/C3D), sem vídeo RGB, incompatível com o pipeline baseado em MediaPipe.
> - *KIMORE*: o vídeo RGB só é liberado sob pedido ao autor e assinatura de EULA;
>   o download público traz apenas depth + esqueleto (mesma limitação acima).

## Próximos passos (evolução)

- Calibrar os limiares em `config.py` com o dataset **REHAB24-6** (`calibrar.py`).
- Opcional: treinar um **Isolation Forest** sobre as métricas (ver TODO em `anomaly_detector.py`).
- Integrar com os módulos de áudio e clínico na etapa de fusão.
