import json
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import ffmpeg
except ImportError:
    ffmpeg = None

try:
    import librosa
except ImportError:
    librosa = None

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

from langgraph_ai.tools import (
    SYSTEM_PROMPT_INTERVIEW_GRADE,
    SYSTEM_PROMPT_INTERVIEW_QUESTION,
    groq_chat_json,
)


_WHISPER_MODEL = None


def _get_whisper_model() -> Optional[WhisperModel]:
    global _WHISPER_MODEL

    if WhisperModel is None:
        return None

    if _WHISPER_MODEL is None:
        model_name = os.getenv("INTERVIEW_WHISPER_MODEL", "small")
        _WHISPER_MODEL = WhisperModel(model_name, device="cpu", compute_type="int8")
    return _WHISPER_MODEL


def generate_interview_question(payload: Dict[str, Any]) -> Dict[str, Any]:
    return groq_chat_json(
        system_prompt=SYSTEM_PROMPT_INTERVIEW_QUESTION,
        user_content=json.dumps(payload),
        temperature=0.4,
    )


def grade_interview_answer(payload: Dict[str, Any]) -> Dict[str, Any]:
    return groq_chat_json(
        system_prompt=SYSTEM_PROMPT_INTERVIEW_GRADE,
        user_content=json.dumps(payload),
        temperature=0.3,
    )


def transcribe_video(video_path: str) -> Tuple[str, Optional[str]]:
    model = _get_whisper_model()
    if model is None:
        return "", "faster-whisper not available"

    try:
        segments, _ = model.transcribe(video_path, beam_size=5)
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        return transcript, None
    except Exception as exc:
        return "", str(exc)


def _extract_audio_to_wav(video_path: str) -> Optional[str]:
    if ffmpeg is None:
        return None

    temp_dir = tempfile.mkdtemp(prefix="interview-audio-")
    wav_path = os.path.join(temp_dir, "audio.wav")

    try:
        (
            ffmpeg
            .input(video_path)
            .output(wav_path, ac=1, ar=16000, format="wav")
            .overwrite_output()
            .run(quiet=True)
        )
        return wav_path
    except Exception:
        return None


def _score_centered(value: float, center: float, spread: float) -> float:
    if spread <= 0:
        return 50.0
    distance = abs(value - center)
    score = max(0.0, 100.0 - (distance / spread) * 100.0)
    return float(min(100.0, score))


def _clip_score(value: float) -> float:
    return float(max(0.0, min(100.0, value)))


def _analyze_audio_metrics(video_path: str, transcript_text: str) -> Dict[str, float]:
    if librosa is None:
        return {"energy_score": 50.0, "pace_score": 50.0, "duration": 0.0}

    wav_path = _extract_audio_to_wav(video_path)
    if not wav_path:
        return {"energy_score": 50.0, "pace_score": 50.0, "duration": 0.0}

    try:
        audio, sr = librosa.load(wav_path, sr=16000, mono=True)
        duration = librosa.get_duration(y=audio, sr=sr)
        rms = float(np.mean(librosa.feature.rms(y=audio))) if audio.size else 0.0
        rms_db = float(librosa.amplitude_to_db(np.array([rms]), ref=1.0)[0]) if rms > 0 else -80.0

        energy_score = _clip_score((rms_db + 80.0) * 2.0)

        word_count = len([w for w in transcript_text.split() if w.strip()])
        minutes = max(duration / 60.0, 1e-3)
        words_per_minute = word_count / minutes
        pace_score = _score_centered(words_per_minute, center=135.0, spread=90.0)

        return {
            "energy_score": _clip_score(energy_score),
            "pace_score": _clip_score(pace_score),
            "duration": float(duration),
        }
    except Exception:
        return {"energy_score": 50.0, "pace_score": 50.0, "duration": 0.0}


def _analyze_video_expression(video_path: str) -> Dict[str, float]:
    if cv2 is None:
        return {"expression_score": 50.0, "face_presence": 0.0, "smile_ratio": 0.0}

    face_cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    smile_cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_smile.xml")

    face_cascade = cv2.CascadeClassifier(face_cascade_path)
    smile_cascade = cv2.CascadeClassifier(smile_cascade_path)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"expression_score": 50.0, "face_presence": 0.0, "smile_ratio": 0.0}

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frame_interval = max(int(fps * 0.5), 1)

    total_frames = 0
    face_frames = 0
    smile_frames = 0
    frame_index = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_index += 1
        if frame_index % frame_interval != 0:
            continue
        total_frames += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        if len(faces) == 0:
            continue
        face_frames += 1
        (x, y, w, h) = faces[0]
        roi_gray = gray[y : y + h, x : x + w]
        smiles = smile_cascade.detectMultiScale(roi_gray, scaleFactor=1.7, minNeighbors=22)
        if len(smiles) > 0:
            smile_frames += 1

    cap.release()

    face_presence = face_frames / total_frames if total_frames else 0.0
    smile_ratio = smile_frames / face_frames if face_frames else 0.0
    expression_score = _clip_score((face_presence * 0.6 + smile_ratio * 0.4) * 100.0)

    return {
        "expression_score": expression_score,
        "face_presence": float(face_presence),
        "smile_ratio": float(smile_ratio),
    }


def analyze_behavior_metrics(video_path: str, transcript_text: str) -> Dict[str, Any]:
    audio_metrics = _analyze_audio_metrics(video_path, transcript_text)
    video_metrics = _analyze_video_expression(video_path)

    energy_score = audio_metrics.get("energy_score", 50.0)
    pace_score = audio_metrics.get("pace_score", 50.0)
    expression_score = video_metrics.get("expression_score", 50.0)

    behavior_score = float(np.mean([energy_score, pace_score, expression_score]))

    return {
        "energy_score": _clip_score(energy_score),
        "pace_score": _clip_score(pace_score),
        "expression_score": _clip_score(expression_score),
        "behavior_score": _clip_score(behavior_score),
        "face_presence": video_metrics.get("face_presence", 0.0),
        "smile_ratio": video_metrics.get("smile_ratio", 0.0),
        "duration_seconds": audio_metrics.get("duration", 0.0),
    }
