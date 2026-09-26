from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import AssistantSettings, CommandLogEntry


class LocalStore:
    """Stores settings and command history in the user's local application data."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path.home() / "AppData" / "Local" / "WindowsVoiceAssistant" / "state.json"

    def load_settings(self) -> AssistantSettings:
        return AssistantSettings.from_dict(self._read().get("settings", {}))

    def save_settings(self, settings: AssistantSettings) -> None:
        data = self._read()
        data["settings"] = settings.to_dict()
        self._write(data)

    def load_history(self) -> list[CommandLogEntry]:
        entries = self._read().get("history", [])
        if not isinstance(entries, list):
            return []
        try:
            return [CommandLogEntry.from_dict(entry) for entry in entries if isinstance(entry, dict)]
        except (KeyError, TypeError, ValueError):
            return []

    def append_history(self, command: str, result: str) -> CommandLogEntry:
        entry = CommandLogEntry(timestamp=datetime.now(), command=command, result=result)
        data = self._read()
        history = data.setdefault("history", [])
        if not isinstance(history, list):
            history = data["history"] = []
        history.append(entry.to_dict())
        self._write(data)
        return entry

    def _read(self) -> dict[str, object]:
        try:
            with self._path.open(encoding="utf-8") as state_file:
                data = json.load(state_file)
                return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _write(self, data: dict[str, object]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._path.with_suffix(".tmp")
        with temporary_path.open("w", encoding="utf-8") as state_file:
            json.dump(data, state_file, ensure_ascii=False, indent=2)
        temporary_path.replace(self._path)
