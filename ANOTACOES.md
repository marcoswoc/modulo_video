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
3. **Dataset: usar KIMORE (vídeo RGB), NÃO o Multi-Gait-Posture.**
   Motivo: o Multi-Gait-Posture (PhysioNet) só tem depth + esqueleto (CSV/C3D),
   sem vídeo RGB, incompatível com o pipeline (MediaPipe usa RGB). Usá-lo forçaria
   uma técnica não ensinada em aula. Datasets na spec são só "sugestão".
   - KIMORE: https://vrai.dii.univpm.it/content/kimore-dataset
   - Download (SharePoint): https://univpm-my.sharepoint.com/:f:/g/personal/p008099_staff_univpm_it/EiwbKIzk6N9NoJQx4J8aubIBx0o7tIa1XwclWp1NmRkA-w
4. **Alinhamento com as aulas:** a Aula 03 ensinou exatamente MediaPipe Pose +
   heurística sobre landmarks. A biomecânica (ângulos/simetria) é extensão natural.
   YOLOv8, gait e leitura de depth NÃO foram ensinados.

## Pendências (próximos passos)

- [ ] Baixar uma AMOSTRA do KIMORE (ex.: 5 sujeitos de CG + 5 de GPP), subir no
      Google Drive e rodar `calibrar.py` para ajustar os limiares em `config.py`.
      ANTES de processar, validar a estrutura com o modo dry-run:
      `python calibrar.py --raiz .../KIMORE_amostra --listar`
      (lista os vídeos e o rótulo saudavel/paciente/desconhecido, sem processar
      e sem precisar de cv2/mediapipe). A rotulagem agora casa por SEGMENTO do
      caminho (CG -> saudavel; GPP/BackPain/Parkinson/Stroke -> paciente). Se
      aparecer "desconhecido", ajustar TOKENS_SAUDAVEL/TOKENS_PACIENTE no topo
      de `calibrar.py`. Se houver vídeos de depth junto, filtrar com
      `--filtro-nome rgb`.
- [ ] Versionar um JSON de exemplo em `data/exemplos/` (e o CSV de calibração).
- [ ] Escrever o relatório técnico da parte de vídeo (fluxo, modelos, métricas,
      exemplos, justificativa do dataset).
- [ ] Gravar o vídeo/demo de até 15 min (o `_web.mp4` anotado serve).

## Pontos para levar ao GRUPO (integração)

1. **Azure é obrigatório** no módulo de áudio (spec exige Azure Speech to Text +
   Text Analytics). O plano do time estava vago nisso.
2. **patient_id igual entre os 3 módulos** (vídeo/áudio/clínico), senão a fusão
   não consegue juntar os alertas do mesmo paciente.
3. Avisar que a parte de vídeo trocou o dataset para KIMORE (motivo acima).

## Como rodar (resumo)

```bash
# Colab: célula de instalação já remove o tensorflow (conflito com mediapipe).
python main.py --video data/entrada/video.mp4 --patient-id video_001 \
               --saida data/saida/video_001.json --anotado data/saida/video_001_anotado.mp4

# Máquina fraca: desativa YOLOv8
python main.py --video data/entrada/video.mp4 --sem-objetos

# Calibração com dataset
# 1) valida a estrutura de pastas (dry-run, não processa):
python calibrar.py --raiz "/content/drive/MyDrive/KIMORE_amostra" --listar
# 2) processa e sugere limiares:
python calibrar.py --raiz "/content/drive/MyDrive/KIMORE_amostra" --pular-frames 6 --max 40
# (opcional) se houver vídeos de depth junto dos RGB:
python calibrar.py --raiz "/content/drive/MyDrive/KIMORE_amostra" --listar --filtro-nome rgb
```
