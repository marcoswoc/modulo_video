"""
object_detector.py
-------------------
ETAPA 1b do pipeline: VIDEO -> DETECCAO DE OBJETOS/PESSOAS (YOLOv8).

Complementa a analise postural (MediaPipe/OpenPose) com deteccao de objetos
via YOLOv8 (modelo pre-treinado na base COCO). Aqui focamos em EVENTOS de
contexto e seguranca que a pose sozinha nao captura bem:

  - CONTAGEM de pessoas no quadro (paciente + fisioterapeuta?);
  - PACIENTE AUSENTE / rastreamento perdido (nenhuma pessoa detectada);
  - possivel QUEDA (a "caixa" da pessoa fica mais larga que alta, o que
    sugere alguem deitado/no chao em vez de em pe).

Saida: uma lista de registros por frame, no mesmo espirito do pose_extractor:
    {
        "frame": 12,
        "timestamp": 0.4,          # segundos
        "n_pessoas": 1,
        "pessoas": [
            {"bbox": (x1, y1, x2, y2), "conf": 0.92, "razao_wh": 0.42},
            ...
        ],
    }
As coordenadas da bbox estao em PIXELS (formato nativo do YOLO).
'razao_wh' = largura / altura da caixa (>= 1 sugere pessoa deitada).
"""

from __future__ import annotations

import cv2

from config import YOLO_MODELO, YOLO_CONFIANCA

# Na base COCO, a classe 0 e "person". So nos interessa pessoas aqui.
_CLASSE_PESSOA = 0


def detectar_objetos(caminho_video: str, verbose: bool = True) -> list[dict]:
    """
    Percorre o video com o YOLOv8 e devolve, por frame, as pessoas detectadas.

    Parametros
    ----------
    caminho_video : str
        Caminho do video de entrada.
    verbose : bool
        Se True, imprime um aviso simples de progresso.

    Retorna
    -------
    list[dict]
        Um registro por frame com a contagem e as caixas das pessoas.
    """
    # Precisamos do FPS para converter indice de frame em segundos.
    cap = cv2.VideoCapture(caminho_video)
    if not cap.isOpened():
        raise FileNotFoundError(f"Nao consegui abrir o video: {caminho_video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()

    # Import "preguicoso": so exige ultralytics/PyTorch quando o YOLO e usado.
    # Assim, rodar com --sem-objetos nao precisa dessas dependencias instaladas.
    from ultralytics import YOLO

    # Carrega o modelo (baixa o .pt na primeira vez). 'yolov8n' = nano, leve.
    modelo = YOLO(YOLO_MODELO)

    # stream=True processa frame a frame sem estourar a memoria com videos longos.
    resultados = modelo.predict(
        source=caminho_video,
        stream=True,
        classes=[_CLASSE_PESSOA],
        conf=YOLO_CONFIANCA,
        verbose=False,
    )

    registros: list[dict] = []
    for indice_frame, res in enumerate(resultados):
        pessoas = []
        for box in res.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            largura = x2 - x1
            altura = y2 - y1
            razao_wh = (largura / altura) if altura > 0 else 0.0
            pessoas.append({
                "bbox": (x1, y1, x2, y2),
                "conf": float(box.conf[0]),
                "razao_wh": razao_wh,
            })

        registros.append({
            "frame": indice_frame,
            "timestamp": indice_frame / fps,
            "n_pessoas": len(pessoas),
            "pessoas": pessoas,
        })

    if verbose:
        print(f"      YOLOv8: {len(registros)} frames analisados.")
    return registros


def _pessoa_principal(pessoas: list[dict]) -> dict:
    """A pessoa 'principal' e a de maior area (assumimos ser o paciente em foco)."""
    def area(p):
        x1, y1, x2, y2 = p["bbox"]
        return (x2 - x1) * (y2 - y1)
    return max(pessoas, key=area)


def extrair_metricas_objetos(registros_obj: list[dict], limiar_queda: float) -> dict:
    """
    Agrega os registros do YOLO em metricas consumidas pelo anomaly_detector.

    Parametros
    ----------
    registros_obj : list[dict]
        Saida de detectar_objetos().
    limiar_queda : float
        Razao largura/altura a partir da qual consideramos "possivel queda".

    Retorna
    -------
    dict com:
        - prop_frames_sem_pessoa : fracao de frames sem nenhuma pessoa (0..1)
        - prop_frames_queda      : fracao de frames (com pessoa) em possivel queda
        - max_pessoas            : maior numero de pessoas visto em um frame
        - media_pessoas          : media de pessoas por frame
    """
    total = len(registros_obj)
    if total == 0:
        return {
            "prop_frames_sem_pessoa": 1.0,
            "prop_frames_queda": 0.0,
            "max_pessoas": 0,
            "media_pessoas": 0.0,
        }

    frames_sem_pessoa = 0
    frames_queda = 0
    contagens = []

    for r in registros_obj:
        n = r["n_pessoas"]
        contagens.append(n)
        if n == 0:
            frames_sem_pessoa += 1
            continue
        principal = _pessoa_principal(r["pessoas"])
        if principal["razao_wh"] >= limiar_queda:
            frames_queda += 1

    frames_com_pessoa = total - frames_sem_pessoa
    return {
        "prop_frames_sem_pessoa": frames_sem_pessoa / total,
        "prop_frames_queda": (frames_queda / frames_com_pessoa) if frames_com_pessoa > 0 else 0.0,
        "max_pessoas": max(contagens),
        "media_pessoas": sum(contagens) / total,
    }
