# 🚀 Elaris Autostart-Gatekeeper
# Startet beim Windows-Login automatisch die Gatekeeper-GUI und bei Erfolg den Auto-Integritätslauf

import subprocess
from pathlib import Path
from datetime import datetime
import time

try:
    from win10toast import ToastNotifier
except ImportError:
    subprocess.run(["pip", "install", "win10toast"], capture_output=True)
    from win10toast import ToastNotifier

BASE = Path(__file__).parent
LOG = BASE / "autostart_log.txt"
STARTUP_GUI = BASE / "startup_manager_gui.py"
AUTO_RUN = BASE / "auto_gatekeeper_run.py"

def log(msg: str):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a", encoding="utf-8", errors="ignore") as f:
        f.write(f"[{stamp}] {msg}\n")

def show_notification(title: str, message: str, duration: int = 6):
    """Zeigt Desktop-Benachrichtigung (blockierend)"""
    try:
        toast = ToastNotifier()
        toast.show_toast(title, message, duration=duration, threaded=False)
        time.sleep(1)
    except Exception as e:
        log(f"[WARN] Benachrichtigung fehlgeschlagen: {e}")

def run_gui():
    """Startet die Haupt-GUI"""
    if STARTUP_GUI.exists():
        log(f"Starte GUI: {STARTUP_GUI}")
        subprocess.Popen(["python", str(STARTUP_GUI)], creationflags=subprocess.CREATE_NO_WINDOW)
        show_notification("🧠 Elaris System", "Haupt-Gatekeeper gestartet ✅")
    else:
        log("[FEHLER] startup_manager_gui.py nicht gefunden!")
        show_notification("❌ Elaris System", "Start-GUI nicht gefunden!", 8)

def run_auto_gatekeeper():
    """Startet den automatischen Integritätslauf"""
    if AUTO_RUN.exists():
        log("Starte automatischen Integritätslauf...")
        subprocess.Popen(["python", str(AUTO_RUN)], creationflags=subprocess.CREATE_NO_WINDOW)
        show_notification("🧠 Elaris System", "Integritätsprüfung gestartet...", 6)
    else:
        log("[FEHLER] auto_gatekeeper_run.py nicht gefunden!")

def main():
    log("=== Autostart-Gatekeeper gestartet ===")
    run_gui()

    # Warte 20 Sekunden, um GUI-Start zu ermöglichen
    time.sleep(20)

    run_auto_gatekeeper()
    log("=== Autostart-Sequenz beendet ===")

if __name__ == "__main__":
    main()
