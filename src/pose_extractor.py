"""
pose_extractor.py
-----------------
ETAPA 1 do pipeline: VIDEO -> PONTOS-CHAVE (keypoints).

Usa o MediaPipe Pose (equivalente pratico ao OpenPose citado no desafio) para,
a cada frame do video, estimar a posicao de 33 pontos do corpo (ombros,
quadris, joelhos, tornozelos etc.).

Saida: uma lista de frames, onde cada frame eh um dicionario:
    {
        "frame": 12,
        "timestamp": 0.4,           # segundos
        "landmarks": {
            "ombro_esq": (x, y, visibility),
            ...
        }
    }
As coordenadas x, y sao NORMALIZADAS (0 a 1) em relacao ao tamanho do frame.
"""

from __future__ import annotations

import platform

import cv2
import mediapipe as mp

from config import LANDMARKS

mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils


def _abrir_gravador(caminho: str, fps: float, largura: int, altura: int) -> "cv2.VideoWriter":
    """
    Cria o VideoWriter escolhendo o codec conforme o sistema operacional.

    - Windows: 'mp4v' funciona de imediato (o wheel do opencv-python nao traz
      o codec H264 no Windows, entao evitamos 'avc1' para nao falhar).
    - Linux/Mac (inclusive Google Colab): tenta 'avc1' (H264, melhor
      compatibilidade com navegadores e players) e, se nao estiver disponivel,
      cai de volta para 'mp4v'.

    Testa cada codec de fato abrindo o gravador; se nenhum abrir, levanta erro.
    """
    if platform.system() == "Windows":
        candidatos = ["mp4v"]
    else:
        candidatos = ["avc1", "mp4v"]

    for codec in candidatos:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(caminho, fourcc, fps, (largura, altura))
        if writer.isOpened():
            return writer
        writer.release()  # nao abriu com esse codec; tenta o proximo

    raise RuntimeError(
        f"Nao consegui abrir o gravador de video para: {caminho} "
        f"(codecs tentados: {candidatos})"
    )


def extrair_pose(caminho_video: str, salvar_anotado: str | None = None) -> list[dict]:
    """
    Percorre o video frame a frame e extrai os landmarks do corpo.

    Parametros
    ----------
    caminho_video : str
        Caminho do arquivo de video de entrada (.mp4, .avi, ...).
    salvar_anotado : str | None
        Se informado, grava um novo video com o esqueleto desenhado
        (otimo para a demonstracao de 15 min exigida no Tech Challenge).

    Retorna
    -------
    list[dict]
        Um registro por frame com os landmarks nomeados.
    """
    cap = cv2.VideoCapture(caminho_video)
    if not cap.isOpened():
        raise FileNotFoundError(f"Nao consegui abrir o video: {caminho_video}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0  # fallback se o video nao informar
    largura = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    altura = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Se pediram para salvar o video anotado, preparamos o gravador.
    # O codec eh escolhido automaticamente conforme o sistema operacional.
    writer = None
    if salvar_anotado:
        writer = _abrir_gravador(salvar_anotado, fps, largura, altura)

    registros: list[dict] = []

    # O 'with' garante que o modelo seja liberado da memoria no final.
    with mp_pose.Pose(
        static_image_mode=False,      # video (usa rastreamento entre frames)
        model_complexity=1,           # 0=rapido, 1=equilibrado, 2=preciso
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as pose:

        indice_frame = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break  # fim do video

            # MediaPipe espera imagem em RGB; OpenCV entrega em BGR.
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resultado = pose.process(frame_rgb)

            if resultado.pose_landmarks:
                pontos = resultado.pose_landmarks.landmark
                landmarks_nomeados = {}
                for nome, idx in LANDMARKS.items():
                    p = pontos[idx]
                    landmarks_nomeados[nome] = (p.x, p.y, p.visibility)

                registros.append({
                    "frame": indice_frame,
                    "timestamp": indice_frame / fps,
                    "landmarks": landmarks_nomeados,
                })

                # Desenha o esqueleto sobre o frame para o video anotado.
                if writer is not None:
                    mp_draw.draw_landmarks(
                        frame,
                        resultado.pose_landmarks,
                        mp_pose.POSE_CONNECTIONS,
                    )

            if writer is not None:
                writer.write(frame)

            indice_frame += 1

    cap.release()
    if writer is not None:
        writer.release()

    return registros
