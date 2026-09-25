# Voice Assistant (VA)

A lightweight, background Windows voice assistant designed for rapid desktop automation with high sensitivity audio capture and pronunciation/accent tolerance.

## Key Features

- **Global Hotkey Activation**: Press the Insert key from any application to activate the voice assistant overlay.
- **Accent & Pronunciation Tolerance**:
  - Implements phonetic encoding (Soundex) and fuzzy string matching (difflib, $\ge 0.70$ similarity threshold) to understand words even with imprecise pronunciation or regional accents.
  - Inspects multiple recognition candidates (show_all=True) from Google Speech API with primary en-IN (Indian English) and en-US fallback.
- **Optimized Audio Capture**:
  - Background ambient noise calibration with safety bounds ( - 450$) so the microphone never goes deaf from room noise spikes.
  - Immediate audio capture on trigger without blocking speech start.
- **Single-Instance Protection**:
  - Built-in Windows named mutex (Local\AssistantPy_SingleInstance_Mutex) ensures only one background process runs, preventing hotkey and microphone buffer collisions.
- **Extensible Configuration**:
  - Custom applications and websites can be added via ssistant_config.json without modifying code.

---

## Supported Commands

| Category | Commands / Examples |
| :--- | :--- |
| **Web & Search** | search for <query>, google <query>, open <website> |
| **Applications** | chrome, rave, s code / code, 
otepad, calculator, paint, cmd, powershell, whatsapp, discord, 	ask manager, settings, ile explorer |
| **Folders** | documents, downloads, pictures, desktop |
| **System** | olume up, olume down, mute / unmute, lock, screenshot, shutdown (60s timer), cancel shutdown, estart, sleep |
| **Information** | 	ime, date / 	oday |

---

## Configuration (ssistant_config.json)

Configure speech parameters, custom applications, and websites:

`json
{
    "settings": {
        "language": "en-IN",
        "fallback_language": "en-US",
        "fuzzy_threshold": 0.70,
        "energy_threshold": 250,
        "dynamic_energy_threshold": true,
        "listen_timeout": 6,
        "phrase_time_limit": 8,
        "pause_threshold": 1.0,
        "beep": true
    },
    "apps": {
        "spotify": "C:\\Users\\<User>\\AppData\\Roaming\\Spotify\\Spotify.exe"
    },
    "websites": {
        "github": "https://github.com",
        "youtube": "https://youtube.com"
    }
}
`

---

## Installation & Setup

1. **Install Prerequisites**:
   `ash
   pip install speechrecognition pynput pyaudio pillow
   `
   *(Optional for voice output: pip install pyttsx3)*

2. **Run in Background**:
   `ash
   pythonw assistant.py
   `

3. **Auto-Start on Windows Boot**:
   - Press Win + R, type shell:startup, and press Enter.
   - Create a shortcut pointing to:
     `
     Target: pythonw.exe "C:\Path\To\assistant.py"
     Start in: C:\Path\To\
     `

---

## License

This project is licensed under the [MIT License](LICENSE).
