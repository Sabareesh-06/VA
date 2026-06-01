from pynput import keyboard
import winsound

def on_press(key):
    try:
        print(f"Key pressed: {key}")
        # Beep every time you press a key so you don't even have to look at the screen
        winsound.Beep(500, 100) 
        
        if key == keyboard.Key.f4:
            print("!!! F4 SUCCESS !!!")
            winsound.Beep(1000, 500)
    except Exception as e:
        print(f"Error: {e}")

print("Listener started. Press keys to test. Press Ctrl+C to stop.")

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()