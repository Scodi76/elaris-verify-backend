# 🛰️ Elaris Clean Trigger – Silent Bridge zum Startup Manager
# Pfad: C:\Elaris_KI_Versions\Elairs_gatekeeper\tools\elaris_clean_trigger.py
# Zweck: Unsichtbarer Start des elaris_cleaner_first.py mit Parametern
# Wird vom Startup Manager oder Backend aufgerufen.

import subprocess, sys
from pathlib import Path
import os

BASE = Path(__file__).parent
CLEANER = BASE / "elaris_cleaner_first.py"
LOG_FILE = BASE / "clean_first_log.txt"

def run_cleaner(overwrite=True, silent=True):
    """Startet den Cleaner mit gewünschten Parametern."""
    if not CLEANER.exists():
        print("❌ Cleaner-Skript nicht gefunden:", CLEANER)
        return False

    args = ["python", str(CLEANER)]
    if overwrite:
        args.append("--overwrite")
    if silent:
        args.append("--silent")

    try:
        subprocess.Popen(
            args,
            cwd=BASE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    except Exception as e:
        print(f"❌ Fehler beim Start des Cleaners: {e}")
        return False


if __name__ == "__main__":
    ok = run_cleaner(overwrite=True, silent=True)
    if ok:
        print(f"🧩 Silent-Cleaner gestartet (Log: {LOG_FILE})")
    else:
        print("⚠️ Cleaner konnte nicht gestartet werden.")
