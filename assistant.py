import tkinter as tk
from pynput import keyboard
import speech_recognition as sr
import subprocess
import os
import re
import sys
import json
import time
import ctypes
import logging
import threading
import webbrowser
import winsound
import difflib
from datetime import datetime

# ---------------------------------------------------------------------------
# Optional text-to-speech. Falls back to silent/visual-only mode if pyttsx3
# is not installed, so the assistant still runs cleanly.
# ---------------------------------------------------------------------------
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

TRIGGER_KEY = keyboard.Key.insert

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "assistant.log")
CONFIG_FILE = os.path.join(BASE_DIR, "assistant_config.json")

# ---------------------------------------------------------------------------
# Logging - every command, match score, and error is recorded with timestamp
# ---------------------------------------------------------------------------
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ---------------------------------------------------------------------------
# Single-Instance Mutex: Ensures only one assistant instance runs at a time.
# Prevents duplicate background processes from clashing over hotkeys & mic.
# ---------------------------------------------------------------------------
SINGLE_INSTANCE_MUTEX_NAME = "Local\\AssistantPy_SingleInstance_Mutex"
_MUTEX_HANDLE = None

def acquire_single_instance_lock(name=SINGLE_INSTANCE_MUTEX_NAME):
    global _MUTEX_HANDLE
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, name)
    last_error = kernel32.GetLastError()
    ERROR_ALREADY_EXISTS = 183
    if last_error == ERROR_ALREADY_EXISTS:
        if mutex:
            kernel32.CloseHandle(mutex)
        return None
    _MUTEX_HANDLE = mutex
    return mutex


# ---------------------------------------------------------------------------
# Config loader with settings support
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "settings": {
        "language": "en-IN",
        "fallback_language": "en-US",
        "fuzzy_threshold": 0.70,
        "energy_threshold": 250,
        "dynamic_energy_threshold": True,
        "listen_timeout": 6,
        "phrase_time_limit": 8,
        "pause_threshold": 0.8,
        "beep": True
    },
    "apps": {},
    "websites": {}
}

def load_config():
    """Loads configuration with user-defined settings, apps, and websites."""
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
        except Exception as e:
            logging.error(f"Could not create config file: {e}")
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            data.setdefault("settings", DEFAULT_CONFIG["settings"])
            data.setdefault("apps", {})
            data.setdefault("websites", {})
            # Merge any missing settings
            for k, v in DEFAULT_CONFIG["settings"].items():
                data["settings"].setdefault(k, v)
            return data
    except Exception as e:
        logging.error(f"Could not read config file: {e}")
        return DEFAULT_CONFIG


# ---------------------------------------------------------------------------
# Phonetic Encoding (Soundex) for matching mispronounced words
# ---------------------------------------------------------------------------
def soundex(word):
    """Generates a 4-character Soundex code for phonetic similarity."""
    if not word:
        return ""
    word = re.sub(r"[^A-Za-z]", "", word).upper()
    if not word:
        return ""
    mapping = {
        'B': '1', 'F': '1', 'P': '1', 'V': '1',
        'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
        'D': '3', 'T': '3',
        'L': '4',
        'M': '5', 'N': '5',
        'R': '6'
    }
    first = word[0]
    enc = first
    prev = mapping.get(first, '0')
    for c in word[1:]:
        code = mapping.get(c, '0')
        if code != '0' and code != prev:
            enc += code
            prev = code
        elif code == '0':
            prev = '0'
    return (enc.replace('0', '') + '000')[:4]


# ---------------------------------------------------------------------------
# Comprehensive Command Aliases & Mispronunciations
# ---------------------------------------------------------------------------
COMMAND_ALIASES = {
    # System Controls (cancel shutdown placed first for priority)
    "cancel shutdown": [
        "cancel shutdown", "cancel shut down", "abort shutdown", "stop shutdown",
        "don't shut down", "dont shutdown", "cancel restart"
    ],
    "shutdown": [
        "shutdown", "shut down", "shut off", "power off", "turn off pc",
        "turn off computer", "switch off", "power down", "saddam", "shat down", "shot down"
    ],
    "restart": ["restart", "reboot", "restart pc", "restart computer"],
    "sleep": ["sleep", "go to sleep", "suspend", "standby", "hibernate"],
    "lock": ["lock", "lock pc", "lock screen", "lock workstation"],
    "mute": ["mute", "unmute", "silent", "silence", "toggle sound", "toggle mute"],
    "volume up": [
        "volume up", "vol up", "sound up", "increase volume", "raise volume",
        "louder", "boost volume", "audio up"
    ],
    "volume down": [
        "volume down", "vol down", "sound down", "decrease volume", "lower volume",
        "reduce volume", "quieter", "audio down"
    ],
    "screenshot": [
        "screenshot", "screen shot", "take screenshot", "take screen shot",
        "capture screen", "snapshot", "screen snap", "print screen"
    ],

    # Applications
    "notepad": [
        "notepad", "notepud", "notepat", "note pad", "text editor", "not pad", "notebook"
    ],
    "chrome": [
        "chrome", "crome", "chrom", "krome", "google chrome", "google", "browser"
    ],
    "brave": ["brave", "brav", "brave browser", "bravo"],
    "code": [
        "code", "vscode", "vs code", "visual studio code", "vs studio",
        "vissual code", "editor", "v s code", "bs code", "bs call", "bescom",
        "bs com", "ds code", "ps4", "bs4", "vs", "v s", "studio code", "visual studio"
    ],
    "discord": ["discord", "dis cord", "discort", "discurd", "this cord"],
    "whatsapp": [
        "whatsapp", "whats app", "whatsup", "watssup", "wattsapp", "wat sap", "what app"
    ],
    "cmd": [
        "cmd", "command prompt", "terminal", "command", "prompt", "command promt"
    ],
    "powershell": ["powershell", "power shell", "pshell", "shell"],
    "calculator": [
        "calculator", "calc", "calci", "calcuter", "calculation", "calculater", "kalc"
    ],
    "paint": ["paint", "mspaint", "ms paint", "drawing"],
    "explorer": [
        "explorer", "file explorer", "files", "my computer", "this pc",
        "folders", "file manager"
    ],
    "task manager": [
        "task manager", "taskmanager", "task mgr", "taskmgr", "processes", "task mange"
    ],
    "settings": [
        "settings", "setting", "control panel", "windows settings", "system settings"
    ],

    # Folders
    "documents": ["documents", "document", "doc", "docs", "my documents"],
    "downloads": ["downloads", "download", "my downloads", "down loads"],
    "pictures": ["pictures", "picture", "photos", "images", "my pictures", "photo"],
    "desktop": ["desktop", "desk top", "my desktop"],

    # Time & Date
    "time": ["time", "what time", "what is the time", "current time", "clock", "tell me time"],
    "date": ["date", "today", "current date", "what is the date", "what day is it", "day"]
}

# Pre-compile flattened alias list sorted by phrase length descending
ALL_COMMAND_ITEMS = []
for cmd, aliases in COMMAND_ALIASES.items():
    for alias in aliases:
        ALL_COMMAND_ITEMS.append((cmd, alias))
ALL_COMMAND_ITEMS.sort(key=lambda x: len(x[1]), reverse=True)


def normalize_text(text):
    """Normalizes spoken text by removing punctuation and polite prefixes."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    # Strip conversational filler prefixes
    text = re.sub(r"^(?:please|can you|could you|kindly|hey|assistant|just|now)\s+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def match_command(query, user_config, threshold=0.70):
    """
    Matches spoken query against commands using exact substring, token matching,
    fuzzy string similarity, and Soundex phonetic encoding.
    """
    cleaned = normalize_text(query)
    if not cleaned:
        return None, 0.0, "Empty query"

    tokens = cleaned.split()

    # 1. Parameterized: Search Google
    m = re.search(r"^(?:search for|google|search)\s+(.+)", cleaned)
    if m:
        term = m.group(1).strip()
        return ("search", term), 1.0, f"Search Google: '{term}'"

    # Direct "open <target>"
    m = re.search(r"^(?:open|launch|start|run)\s+(.+)", cleaned)
    target_phrase = m.group(1).strip() if m else cleaned

    # 2. Check Custom Websites and Apps from config
    custom_items = []
    for site, url in user_config.get("websites", {}).items():
        custom_items.append(("website", url, site))
    for app, path in user_config.get("apps", {}).items():
        custom_items.append(("app", path, app))
    custom_items.sort(key=lambda x: len(x[2]), reverse=True)

    for c_type, c_val, c_name in custom_items:
        pattern = r"\b" + re.escape(c_name.lower()) + r"\b"
        if re.search(pattern, target_phrase) or re.search(pattern, cleaned):
            return (c_type, c_val, c_name), 1.0, f"Custom {c_type}: {c_name}"

    # 3. Exact word/phrase match on built-in commands (longest alias first)
    for cmd, alias in ALL_COMMAND_ITEMS:
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, target_phrase) or re.search(pattern, cleaned):
            return ("builtin", cmd), 1.0, f"Matched '{alias}'"

    # 4. Fuzzy & Phonetic Matching
    best_match = None
    best_score = 0.0
    best_alias = ""

    # Check custom apps/websites fuzzy
    for c_type, c_val, c_name in custom_items:
        name_lower = c_name.lower()
        score = difflib.SequenceMatcher(None, target_phrase, name_lower).ratio()
        if score > best_score:
            best_score = score
            best_match = (c_type, c_val, c_name)
            best_alias = c_name
        for t in tokens:
            t_score = difflib.SequenceMatcher(None, t, name_lower).ratio()
            if t_score > best_score:
                best_score = t_score
                best_match = (c_type, c_val, c_name)
                best_alias = f"{t} ~ {c_name}"

    # Check built-in commands fuzzy and phonetic
    for cmd, alias in ALL_COMMAND_ITEMS:
        # Full phrase similarity
        score = difflib.SequenceMatcher(None, target_phrase, alias).ratio()
        if score > best_score:
            best_score = score
            best_match = ("builtin", cmd)
            best_alias = alias

        # Token-by-token check
        for t in tokens:
            t_score = difflib.SequenceMatcher(None, t, alias).ratio()
            if t_score > best_score:
                best_score = t_score
                best_match = ("builtin", cmd)
                best_alias = f"{t} ~ {alias}"

            # Soundex phonetic check for words of 3+ letters
            if len(t) >= 3 and len(alias) >= 3:
                if soundex(t) == soundex(alias):
                    p_score = max(0.85, t_score)
                    if p_score > best_score:
                        best_score = p_score
                        best_match = ("builtin", cmd)
                        best_alias = f"Phonetic {t}=={alias}"

    if best_score >= threshold and best_match:
        return best_match, best_score, f"Fuzzy: {best_alias} ({best_score:.2f})"

    return None, 0.0, "No matching command"


class AssistantApp:
    def __init__(self):
        self.config = load_config()
        self.settings = self.config.get("settings", DEFAULT_CONFIG["settings"])
        self.listening = False

        # Configure Speech Recognizer
        self.r = sr.Recognizer()
        self.r.energy_threshold = self.settings.get("energy_threshold", 250)
        self.r.dynamic_energy_threshold = self.settings.get("dynamic_energy_threshold", True)
        self.r.dynamic_energy_adjustment_damping = 0.15
        self.r.dynamic_energy_ratio = 1.5
        self.r.pause_threshold = self.settings.get("pause_threshold", 0.8)
        self.r.non_speaking_duration = 0.4

        # Initial background ambient calibration so opening the mic is instantaneous
        threading.Thread(target=self._calibrate_ambient_background, daemon=True).start()

        if TTS_AVAILABLE:
            try:
                self.tts = pyttsx3.init()
                self.tts.setProperty("rate", 175)
            except Exception as e:
                logging.error(f"TTS init error: {e}")
                self.tts = None
        else:
            self.tts = None

        logging.info("Assistant started with enhanced hearing and pronunciation tolerance.")
        print("Assistant started.")

    def _calibrate_ambient_background(self):
        """Calibrates ambient noise once at startup in background."""
        try:
            with sr.Microphone() as source:
                self.r.adjust_for_ambient_noise(source, duration=0.6)
            # Clamp threshold to ensure microphone remains sensitive and never goes deaf
            self.r.energy_threshold = max(120.0, min(self.r.energy_threshold, 450.0))
            logging.info(f"Initial ambient calibration complete. Threshold: {self.r.energy_threshold:.1f}")
        except Exception as e:
            logging.warning(f"Background ambient calibration skipped: {e}")

    def speak(self, text):
        print("Assistant:", text)
        if self.tts:
            try:
                self.tts.say(text)
                self.tts.runAndWait()
            except Exception as e:
                logging.error(f"TTS error: {e}")

    # -----------------------------------------------------------------
    # UI + listening flow
    # -----------------------------------------------------------------
    def open_ui_and_listen(self):
        if self.listening:
            return
        self.listening = True

        root = tk.Tk()
        root.title("Assistant")
        root.geometry("400x140")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg="#1a1a1a")

        # Center near top of the screen
        screen_w = root.winfo_screenwidth()
        root.geometry(f"+{(screen_w - 400) // 2}+40")

        label = tk.Label(
            root,
            text="Listening...",
            fg="#00d1ff",
            bg="#1a1a1a",
            font=("Verdana", 16, "bold"),
            wraplength=360,
        )
        label.pack(expand=True, pady=(15, 2))

        sub_label = tk.Label(
            root,
            text="Speak your command...",
            fg="#7fffb2",
            bg="#1a1a1a",
            font=("Verdana", 10),
            wraplength=360,
        )
        sub_label.pack(pady=(0, 15))

        def safe_update(main_text, sub_text=""):
            try:
                label.config(text=main_text)
                sub_label.config(text=sub_text)
                root.update()
            except tk.TclError:
                pass

        def capture_voice():
            try:
                # Reload config each listen so changes to config take effect immediately
                self.config = load_config()
                self.settings = self.config.get("settings", DEFAULT_CONFIG["settings"])
                threshold = self.settings.get("fuzzy_threshold", 0.70)
                primary_lang = self.settings.get("language", "en-IN")
                fallback_lang = self.settings.get("fallback_language", "en-US")
                listen_timeout = self.settings.get("listen_timeout", 6)
                phrase_limit = self.settings.get("phrase_time_limit", 8)
                self.r.pause_threshold = self.settings.get("pause_threshold", 1.0)
                beep_enabled = self.settings.get("beep", True)

                with sr.Microphone() as source:
                    # Keep energy threshold in ideal sensitive hearing range
                    if self.r.energy_threshold > 450.0:
                        self.r.energy_threshold = 250.0

                    # Signal to user: Mic is live and recording immediately!
                    if beep_enabled:
                        winsound.Beep(1200, 100)

                    safe_update("Listening...", "Speak now...")

                    audio = self.r.listen(
                        source,
                        timeout=listen_timeout,
                        phrase_time_limit=phrase_limit
                    )

                safe_update("Recognizing...", "Analyzing speech...")

                # Retrieve candidate transcripts from Google Speech API
                candidates = []
                try:
                    res = self.r.recognize_google(audio, language=primary_lang, show_all=True)
                    if isinstance(res, dict) and "alternative" in res:
                        candidates = [alt["transcript"] for alt in res["alternative"] if "transcript" in alt]
                    elif isinstance(res, str) and res.strip():
                        candidates = [res.strip()]
                except Exception as e:
                    logging.info(f"Primary language ({primary_lang}) recognition exception: {e}")

                # If no candidates, try fallback language
                if not candidates and fallback_lang and fallback_lang != primary_lang:
                    try:
                        res = self.r.recognize_google(audio, language=fallback_lang, show_all=True)
                        if isinstance(res, dict) and "alternative" in res:
                            candidates = [alt["transcript"] for alt in res["alternative"] if "transcript" in alt]
                        elif isinstance(res, str) and res.strip():
                            candidates = [res.strip()]
                    except Exception as e:
                        logging.info(f"Fallback language ({fallback_lang}) recognition exception: {e}")

                if not candidates:
                    raise sr.UnknownValueError()

                logging.info(f"Speech candidates recognized: {candidates}")

                # Test candidates against the command matcher
                best_match = None
                best_score = 0.0
                best_reason = ""
                matched_query = candidates[0]

                for cand in candidates:
                    match_res, score, reason = match_command(cand, self.config, threshold=threshold)
                    if match_res and score > best_score:
                        best_match = match_res
                        best_score = score
                        best_reason = reason
                        matched_query = cand
                        if score >= 0.99:
                            break  # Exact match, no need to test lower alternatives

                if best_match:
                    logging.info(f"Matched command: {best_match} via {best_reason} on query '{matched_query}'")
                    safe_update(f'"{matched_query}"', "Executing...")
                    result_text = self.execute_action(best_match, matched_query)
                    safe_update(f'"{matched_query}"', result_text)
                else:
                    top_cand = candidates[0]
                    logging.info(f"No command matched query: '{top_cand}'")
                    safe_update(f'"{top_cand}"', "No matching command found")
                    if beep_enabled:
                        winsound.Beep(500, 180)

            except sr.WaitTimeoutError:
                logging.info("No speech detected (timeout).")
                safe_update("No speech detected", "Please try speaking closer to mic")
                if self.settings.get("beep", True):
                    winsound.Beep(400, 200)

            except sr.UnknownValueError:
                logging.info("Speech was not understood.")
                safe_update("Could not understand", "Try speaking clearly or adjust sensitivity")
                if self.settings.get("beep", True):
                    winsound.Beep(400, 200)

            except Exception as e:
                logging.error(f"ERROR during voice capture: {e}")
                safe_update("Something went wrong", str(e)[:40])
                if self.settings.get("beep", True):
                    winsound.Beep(400, 200)

            finally:
                self.listening = False
                root.after(1800, root.destroy)

        threading.Thread(target=capture_voice, daemon=True).start()
        root.mainloop()

    # -----------------------------------------------------------------
    # Command Execution
    # -----------------------------------------------------------------
    def execute_action(self, match, raw_query):
        cmd_type = match[0]

        try:
            # 1. Google Search
            if cmd_type == "search":
                term = match[1]
                webbrowser.open(f"https://www.google.com/search?q={term}")
                return f"Searching Google: '{term}'"

            # 2. Custom Website
            if cmd_type == "website":
                url = match[1]
                name = match[2]
                webbrowser.open(url)
                return f"Opening website: {name}"

            # 3. Custom App
            if cmd_type == "app":
                path = match[1]
                name = match[2]
                subprocess.Popen(path)
                return f"Opening app: {name}"

            # 4. Built-in Commands
            if cmd_type == "builtin":
                action = match[1]

                # Folders
                if action == "documents":
                    os.startfile(os.path.expanduser("~/Documents"))
                    return "Opening Documents"

                elif action == "downloads":
                    os.startfile(os.path.expanduser("~/Downloads"))
                    return "Opening Downloads"

                elif action == "pictures":
                    os.startfile(os.path.expanduser("~/Pictures"))
                    return "Opening Pictures"

                elif action == "desktop":
                    os.startfile(os.path.expanduser("~/Desktop"))
                    return "Opening Desktop"

                # Applications
                elif action == "notepad":
                    subprocess.Popen("notepad.exe")
                    return "Opening Notepad"

                elif action == "chrome":
                    chrome_paths = [
                        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                        "chrome.exe"
                    ]
                    for p in chrome_paths:
                        if os.path.exists(p) or p == "chrome.exe":
                            subprocess.Popen(p)
                            return "Opening Chrome"
                    return "Chrome not found"

                elif action == "brave":
                    brave_paths = [
                        os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"),
                        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
                        "brave.exe"
                    ]
                    for p in brave_paths:
                        if os.path.exists(p) or p == "brave.exe":
                            subprocess.Popen(p)
                            return "Opening Brave"
                    return "Brave not found"

                elif action == "code":
                    code_paths = [
                        os.path.expanduser(r"~\AppData\Local\Programs\Microsoft VS Code\Code.exe"),
                        r"C:\Program Files\Microsoft VS Code\Code.exe",
                        "code.cmd",
                        "code"
                    ]
                    for p in code_paths:
                        if os.path.exists(p) or p in ("code.cmd", "code"):
                            subprocess.Popen(p)
                            return "Opening VS Code"
                    return "VS Code not found"

                elif action == "discord":
                    os.system("start discord:")
                    return "Opening Discord"

                elif action == "whatsapp":
                    os.system('start "" "whatsapp:"')
                    return "Opening WhatsApp"

                elif action == "cmd":
                    subprocess.Popen("cmd.exe")
                    return "Opening Command Prompt"

                elif action == "powershell":
                    subprocess.Popen("powershell.exe")
                    return "Opening PowerShell"

                elif action == "calculator":
                    subprocess.Popen("calc.exe")
                    return "Opening Calculator"

                elif action == "paint":
                    subprocess.Popen("mspaint.exe")
                    return "Opening Paint"

                elif action == "explorer":
                    subprocess.Popen("explorer.exe")
                    return "Opening File Explorer"

                elif action == "task manager":
                    subprocess.Popen("taskmgr.exe")
                    return "Opening Task Manager"

                elif action == "settings":
                    os.system("start ms-settings:")
                    return "Opening Settings"

                # System Controls
                elif action == "lock":
                    ctypes.windll.user32.LockWorkStation()
                    return "Locking workstation"

                elif action == "mute":
                    self._send_media_key(0xAD)
                    return "Toggled mute"

                elif action == "volume up":
                    for _ in range(4):
                        self._send_media_key(0xAF)
                    return "Volume up"

                elif action == "volume down":
                    for _ in range(4):
                        self._send_media_key(0xAE)
                    return "Volume down"

                elif action == "shutdown":
                    self.speak("Shutting down in 60 seconds. Say cancel shutdown to stop it.")
                    os.system("shutdown /s /t 60")
                    return "Shutdown scheduled (60s)"

                elif action == "cancel shutdown":
                    os.system("shutdown /a")
                    return "Shutdown cancelled"

                elif action == "restart":
                    self.speak("Restarting in 60 seconds. Say cancel shutdown to stop it.")
                    os.system("shutdown /r /t 60")
                    return "Restart scheduled (60s)"

                elif action == "sleep":
                    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
                    return "Going to sleep"

                elif action == "screenshot":
                    self._take_screenshot()
                    return "Screenshot saved to Pictures"

                # Time and Date
                elif action == "time":
                    now = datetime.now().strftime("%I:%M %p")
                    self.speak(f"It's {now}")
                    return f"Time: {now}"

                elif action == "date":
                    today = datetime.now().strftime("%A, %B %d, %Y")
                    self.speak(today)
                    return today

            return "Unknown command action"

        except Exception as e:
            logging.error(f"Action execution error: {e}")
            return f"Error: {e}"

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    @staticmethod
    def _send_media_key(vk_code):
        """Sends a virtual key press for volume/mute control."""
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)

    @staticmethod
    def _take_screenshot():
        try:
            import PIL.ImageGrab as ImageGrab
            pictures_dir = os.path.expanduser("~/Pictures")
            os.makedirs(pictures_dir, exist_ok=True)
            filename = os.path.join(
                pictures_dir,
                f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            ImageGrab.grab().save(filename)
            logging.info(f"Screenshot saved: {filename}")
        except Exception as e:
            logging.error(f"Screenshot failed: {e}")


if __name__ == "__main__":
    # Ensure only a single instance runs
    mutex = acquire_single_instance_lock()
    if not mutex:
        logging.warning("Another instance of Assistant is already running. Exiting duplicate instance.")
        sys.exit(0)

    app = AssistantApp()

    def on_press(key):
        if key == TRIGGER_KEY:
            print("Insert pressed.")
            logging.info("Trigger key pressed.")
            threading.Thread(target=app.open_ui_and_listen, daemon=True).start()

    print("Assistant is running in background...")
    logging.info("Assistant is running in background...")

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()
