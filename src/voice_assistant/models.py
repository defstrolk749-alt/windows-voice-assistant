from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum


class SpeechProcessingMode(StrEnum):
    LOCAL = "local"
    CLOUD = "cloud"


@dataclass(slots=True)
class AssistantSettings:
    wake_word_enabled: bool = True
    wake_phrase: str = "ассистент"
    speech_processing_mode: SpeechProcessingMode = SpeechProcessingMode.LOCAL

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "AssistantSettings":
        mode = value.get("speech_processing_mode", SpeechProcessingMode.LOCAL)
        try:
            speech_processing_mode = SpeechProcessingMode(str(mode))
        except ValueError:
            speech_processing_mode = SpeechProcessingMode.LOCAL
        return cls(
            wake_word_enabled=bool(value.get("wake_word_enabled", True)),
            wake_phrase=str(value.get("wake_phrase", "ассистент")).strip() or "ассистент",
            speech_processing_mode=speech_processing_mode,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class CommandLogEntry:
    timestamp: datetime
    command: str
    result: str

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "CommandLogEntry":
        return cls(
            timestamp=datetime.fromisoformat(str(value["timestamp"])),
            command=str(value["command"]),
            result=str(value["result"]),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "command": self.command,
            "result": self.result,
        }
