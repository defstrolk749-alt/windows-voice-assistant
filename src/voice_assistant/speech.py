from __future__ import annotations

import json
import os
import queue
import re
from pathlib import Path
from threading import Event

import sounddevice as sd
from PySide6.QtCore import QThread, Signal
from vosk import KaldiRecognizer, Model


class SpeechWorker(QThread):
    """Continuously recognises local microphone audio after a Vosk model is installed."""

    status_changed = Signal(str)
    wake_word_detected = Signal()
    command_recognised = Signal(str)
    recognition_error = Signal(str)

    def __init__(self, wake_phrase: str, model_path: str | None = None) -> None:
        super().__init__()
        self._wake_phrase = self._normalise(wake_phrase)
        self._model_path = Path(model_path or os.environ.get("VOSK_MODEL_PATH", "models/vosk-model-small-ru-0.22"))
        self._stop_event = Event()
        self._awaiting_command = False

    def stop(self) -> None:
        self._stop_event.set()
        self.requestInterruption()

    def run(self) -> None:
        if not self._model_path.is_dir():
            self.recognition_error.emit(
                "Локальная модель речи не найдена. Скачайте Vosk-модель и укажите путь в VOSK_MODEL_PATH."
            )
            return

        audio_queue: queue.Queue[bytes] = queue.Queue()

        def callback(indata: bytes, frames: int, time: object, status: object) -> None:
            del frames, time
            if status:
                self.recognition_error.emit(f"Ошибка микрофона: {status}")
            audio_queue.put(bytes(indata))

        try:
            model = Model(str(self._model_path))
            recognizer = KaldiRecognizer(model, 16000)
            self.status_changed.emit("Ожидание голосовой фразы активации")
            with sd.RawInputStream(
                samplerate=16000,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=callback,
            ):
                while not self._stop_event.is_set():
                    try:
                        audio = audio_queue.get(timeout=0.2)
                    except queue.Empty:
                        continue
                    if recognizer.AcceptWaveform(audio):
                        text = self._result_text(recognizer.Result())
                        self._handle_text(text)
        except Exception as error:
            self.recognition_error.emit(f"Не удалось запустить локальное распознавание: {error}")

    def _handle_text(self, text: str) -> None:
        if not text:
            return
        if not self._awaiting_command:
            if self._wake_phrase in text:
                remainder = text.split(self._wake_phrase, 1)[1].strip()
                self.wake_word_detected.emit()
                if remainder:
                    self.command_recognised.emit(remainder)
                    self.status_changed.emit("Ожидание голосовой фразы активации")
                else:
                    self._awaiting_command = True
                    self.status_changed.emit("Готов принять голосовую команду")
            return

        self._awaiting_command = False
        self.command_recognised.emit(text)
        self.status_changed.emit("Ожидание голосовой фразы активации")

    @staticmethod
    def _result_text(result: str) -> str:
        try:
            return SpeechWorker._normalise(str(json.loads(result).get("text", "")))
        except json.JSONDecodeError:
            return ""

    @staticmethod
    def _normalise(value: str) -> str:
        return re.sub(r"\s+", " ", value.casefold()).strip()
