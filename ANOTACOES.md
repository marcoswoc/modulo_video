# Anotações de continuação (módulo de vídeo)

Documento para retomar o trabalho de qualquer máquina. Resume o estado atual,
as decisões tomadas e o que falta fazer.

## Como retomar em outro computador

```bash
git clone https://github.com/marcoswoc/modulo_video.git
cd modulo_video
```

- Não há Python instalado localmente por escolha: o projeto roda no **Google Colab**.
- Notebook pronto: abra `colab_modulo_video.ipynb` no Colab por este link:
  `https://colab.research.google.com/github/marcoswoc/modulo_video/blob/main/colab_modulo_video.ipynb`
- Repositório: https://github.com/marcoswoc/modulo_video

## Estado atual (o que já está pronto e validado)

- Pipeline completo em 5 etapas + etapa 1b (YOLOv8). Ver `README.md`.
- **Validado no Colab de ponta a ponta**: MediaPipe (pose/biomecânica) + YOLOv8
  (queda/ausência/contagem) + alerta JSON no schema oficial + vídeo anotado.
- Saída de exemplo já gerada (schema oficial do grupo). Exemplo real obtido:
  `score_risco=0.33, nivel_risco=baixo`, anomalias de instabilidade e "múltiplas
  pessoas" (o vídeo de teste tinha 2 pessoas).
- Ferramenta de calibração `calibrar.py` criada (compara saudável x paciente e
  sugere limiares).

## Decisões importantes (contexto que não está óbvio no código)

1. **Schema de saída é o OFICIAL combinado com o grupo** (7 campos:
   patient_id, modulo, tipo_anomalia, score_risco, nivel_risco, descricao,
   recomendacao). Não mudar sem alinhar com o grupo.
2. **YOLOv8 é responsabilidade do Marcos** (parte de vídeo). Já implementado.
   A spec cita "modelos como OpenPose e YOLOv8"; o "como" indica exemplos.
3. **Dataset: usar REHAB24-6 (vídeo RGB público), NÃO o Multi-Gait-Posture nem o KIMORE.**
   Histórico das decisões:
   - Multi-Gait-Posture (PhysioNet): só depth + esqueleto (CSV/C3D), sem RGB.
     Incompatível com MediaPipe (que usa RGB). Descartado.
   - KIMORE: parecia ter RGB, mas o **RGB do KIMORE só é liberado sob pedido ao
     autor + assinatura de EULA**; o download público traz só depth + esqueleto
     (mesma limitação do Multi-Gait-Posture). Descartado.
   - **REHAB24-6 (escolhido)**: vídeo RGB de exercícios de reabilitação, download
     livre no Zenodo (CC-BY-NC, sem EULA). Traz rótulo binário de execução
     correta (1) x incorreta (0) por repetição, o que mapeia direto no conceito de
     anomalia da spec ("movimentos fora do padrão esperado"). Exercícios: abdução
     de braço, transições de braço, flexão, abdução de perna, afundo, agachamento.
     Datasets na spec são só "sugestão", então a troca é legítima.
   - REHAB24-6 (Zenodo): https://zenodo.org/records/13305826
   - Estrutura: `videos.zip` (RGB, 2 câmeras: Camera17 horizontal, Camera18
     vertical) + `Segmentation.csv` (sep=';', 1 linha por repetição).
   - Colunas do CSV: video_id (ex.: PM_000), repetition_number, exercise_id (1-6),
     person_id, first_frame, last_frame, cam17_orientation, mocap_erroneous,
     exercise_subtype, lights_on, extra_person_in_cam17, extra_person_in_cam18,
     correctness (1=correto, 0=incorreto).
   - ATENCAO: correctness varia POR REPETIÇÃO dentro do mesmo vídeo, então a
     calibração fatia por janela [first_frame, last_frame], não por vídeo inteiro.
4. **Alinhamento com as aulas:** a Aula 03 ensinou exatamente MediaPipe Pose +
   heurística sobre landmarks. A biomecânica (ângulos/simetria) é extensão natural.
   YOLOv8, gait e leitura de depth NÃO foram ensinados.

## Pendências (próximos passos)

- [x] Baixar o REHAB24-6 e calibrar. FEITO: exercício 6 (agachamento), Camera17,
      9 gravações, 195 repetições (134 corretas, 61 incorretas). Arquivos reais em
      `videos.zip`/`Segmentation.csv` (na raiz, gitignored). Matching por video_id
      (ex.: PM_029), token `Camera17`.
- [x] Versionar exemplos de saída em `data/exemplos/` (calibracao_agachamento.csv,
      limiares_agachamento.json, alerta_agachamento.json, README.md com tabelas).
      RESULTADO/ACHADO: os chutes do config estavam fora de escala (instabilidade
      0.04 vs real ~0.005-0.014). Para agachamento, inclinação de tronco e
      velocidade separam correto x incorreto; assimetria (métrica de marcha) e
      instabilidade quase não separam agachamento (esperado). Ver
      `data/exemplos/README.md`. NÃO gravei os valores calibrados no config.py
      (fluxo stateless: `calibrar.py --salvar-limiares` + `comparar_video.py`).
- [ ] Escrever o relatório técnico da parte de vídeo (fluxo, modelos, métricas,
      exemplos, justificativa do dataset).
- [ ] Gravar o vídeo/demo de até 15 min (o `_web.mp4` anotado serve).

## Pontos para levar ao GRUPO (integração)

1. **Azure é obrigatório** no módulo de áudio (spec exige Azure Speech to Text +
   Text Analytics). O plano do time estava vago nisso.
2. **patient_id igual entre os 3 módulos** (vídeo/áudio/clínico), senão a fusão
   não consegue juntar os alertas do mesmo paciente.
3. Avisar que a parte de vídeo usa o dataset REHAB24-6 (RGB público; o KIMORE RGB
   exige EULA e não veio no download livre). Motivo detalhado acima.

## Como rodar (resumo)

```bash
# Colab: célula de instalação já remove o tensorflow (conflito com mediapipe).
python main.py --video data/entrada/video.mp4 --patient-id video_001 \
               --saida data/saida/video_001.json --anotado data/saida/video_001_anotado.mp4

# Máquina fraca: desativa YOLOv8
python main.py --video data/entrada/video.mp4 --sem-objetos

# Calibração com dataset REHAB24-6 (rótulo correto/incorreto vem do Segmentation.csv)
# 1) valida CSV + matching de vídeo (dry-run, não processa):
python calibrar.py --raiz "/content/drive/MyDrive/REHAB24-6" --listar
# 2) processa e sugere limiares (recomendado focar 1 exercício por vez):
python calibrar.py --raiz "/content/drive/MyDrive/REHAB24-6" --exercise 6 --pular-frames 3
# (opcional) fixar uma câmera se houver mais de um vídeo por gravação:
python calibrar.py --raiz "/content/drive/MyDrive/REHAB24-6" --camera Camera18 --listar
```
