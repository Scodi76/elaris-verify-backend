# 🧠 Elaris Auto-Startup Launcher (final)
# Startet automatisch beim Windows-Start die GUI startup_manager_gui.py
# Keine automatische Prüfung – reiner GUI-Start

import subprocess
from pathlib import Path
import time
import sys
import os

BASE = Path(__file__).parent
GUI_PATH = BASE / "startup_manager_gui.py"

def main():
    os.system("chcp 65001 >nul")  # UTF-8 für Windows-Terminal
    print("[INFO] Initialisiere Elaris Auto-Startup ...")

    if not GUI_PATH.exists():
        print("[FEHLER] GUI-Datei startup_manager_gui.py wurde nicht gefunden!")
        time.sleep(3)
        sys.exit(1)

    print("[OK] GUI gefunden:", GUI_PATH)
    print("[INFO] Starte Elaris GUI ...")

    try:
        subprocess.Popen(
            ["C:\\Python310\\python.exe", str(GUI_PATH)],
            shell=False,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        print("[OK] GUI-Prozess gestartet.")
    except Exception as e:
        print("[FEHLER] GUI konnte nicht gestartet werden:", e)

    # 2 Sekunden warten, damit der Prozess sichtbar startet
    time.sleep(2)

if __name__ == "__main__":
    main()
