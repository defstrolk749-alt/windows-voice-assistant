# Windows Voice Assistant

Windows desktop voice assistant. Speech processing is local by default. Cloud speech processing is an optional setting.

## Included

- Persistent settings for activation and speech processing mode.
- Local command journal.
- Local voice activation and speech recognition through Vosk.
- A confirmation surface for dangerous actions.

Windows command execution and dictation are planned next.

## Install and run

Requirements: Python 3.11 or newer on Windows, plus a Russian Vosk model.

1. Download and unpack a model, for example `vosk-model-small-ru-0.22`, from [Vosk Models](https://alphacephei.com/vosk/models).
2. Set `VOSK_MODEL_PATH` to the unpacked model directory, or put it in `models/vosk-model-small-ru-0.22`.
3. Install and run the application:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "src"
$env:VOSK_MODEL_PATH = "C:\path\to\vosk-model-small-ru-0.22"
python -m voice_assistant.app
```

Press **Начать прослушивание**, say the configured activation phrase (default: `ассистент`), then say one command. Recognised commands are added to the local journal. The application does not execute them yet.

Local data is stored in `%LOCALAPPDATA%\WindowsVoiceAssistant\state.json`.
