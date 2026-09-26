# Windows Voice Assistant

A Windows desktop voice assistant. Speech processing is local by default. Cloud speech processing is an optional setting.

## Current scope

The first application shell includes:

- Persistent settings for voice activation and speech processing mode.
- A command journal stored locally on the PC.
- Assistant status display.
- A confirmation surface for dangerous actions.

Voice capture, command recognition, Windows controls, and dictation are planned next.

## Run locally

Requirements: Python 3.11 or newer on Windows.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "src"
python -m voice_assistant.app
```

The application stores local data in `%LOCALAPPDATA%\WindowsVoiceAssistant\state.json`.

## Development

```powershell
$env:PYTHONPATH = "src"
python -m voice_assistant.app
```
