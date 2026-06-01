import tkinter as tk
from pynput import keyboard
import speech_recognition as sr
import subprocess
import os
import threading
import winsound

TRIGGER_KEY = keyboard.Key.insert


class AssistantApp:
    def __init__(self):
        self.r = sr.Recognizer()
        print("Assistant started.")

    def open_ui_and_listen(self):
        root = tk.Tk()
        root.title("Assistant")

        root.geometry("350x120")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg="#1e1e1e")

        label = tk.Label(
            root,
            text="Listening...",
            fg="#00d1ff",
            bg="#1e1e1e",
            font=("Verdana", 18, "bold")
        )
        label.pack(expand=True)

        def capture_voice():
            try:
                winsound.Beep(1000, 150)

                with sr.Microphone() as source:
                    print("Listening...")

                    self.r.adjust_for_ambient_noise(source, duration=1)

                    audio = self.r.listen(
                        source,
                        timeout=5,
                        phrase_time_limit=5
                    )

                    query = self.r.recognize_google(audio).lower()

                    print("Recognized:", query)

                    label.config(text=query)
                    root.update()

                    self.execute_command(query)

            except Exception as e:
                print("ERROR:", e)
                label.config(text="Could not hear")

            root.after(1500, root.destroy)

        threading.Thread(target=capture_voice, daemon=True).start()

        root.mainloop()

    def execute_command(self, query):

        print("Executing:", query)

        try:

            if "documents" in query:
                os.startfile(os.path.expanduser("~/Documents"))

            elif "downloads" in query:
                os.startfile(os.path.expanduser("~/Downloads"))

            elif "pictures" in query:
                os.startfile(os.path.expanduser("~/Pictures"))

            elif "desktop" in query:
                os.startfile(os.path.expanduser("~/Desktop"))

            elif "notepad" in query:
                subprocess.Popen("notepad.exe")

            elif "chrome" in query:
                subprocess.Popen(
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe"
                )

            elif "brave" in query:
                subprocess.Popen(
                    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
                )

            elif "code" in query or "visual studio code" in query:
                subprocess.Popen(r"C:\Users\sabar\AppData\Local\Programs\Microsoft VS Code\Code.exe")

            elif "discord" in query:
                os.system("start discord:")

            elif "whatsapp" in query:
                os.system('start "" "whatsapp:"')

            elif "cmd" in query or "command prompt" in query:
                subprocess.Popen("cmd.exe")

            elif "powershell" in query:
                subprocess.Popen("powershell.exe")

            elif "calculator" in query:
                subprocess.Popen("calc.exe")

            elif "paint" in query:
                subprocess.Popen("mspaint.exe")

            elif "explorer" in query:
                subprocess.Popen("explorer.exe")

            else:
                print("No matching command found.")

        except Exception as e:
            print("Launch Error:", e)


app = AssistantApp()


def on_press(key):
    if key == TRIGGER_KEY:
        print("Insert pressed.")
        threading.Thread(
            target=app.open_ui_and_listen,
            daemon=True
        ).start()


print("Assistant is running in background...")

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()