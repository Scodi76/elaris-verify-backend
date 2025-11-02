# 🧠 Elaris Auto-Gatekeeper – Vollautomatischer Integritätscheck mit Auto-Reparatur (KoDa + HS Embed),
# Fallback-Key-Erstellung, Desktop-Benachrichtigung & Fehlerreport
# Version: v4.4 – Stabilisiert & Selbstheilend (Pfad-Fix + Tools-Erkennung + Toast-Fix)
# Erstellt: 2025-10-11

import subprocess
from pathlib import Path
from datetime import datetime
import shutil
import time
import re
import json
import hashlib
import os
import threading

# ======================================================
# 🧩 Pfad-Fix: Erzwingt Hauptverzeichnis als Arbeitsverzeichnis
# ======================================================
BASE = Path(__file__).resolve().parent.parent if (Path(__file__).parent.name == "Tools") else Path(__file__).parent
os.chdir(BASE)
print(f"[INIT] Arbeitsverzeichnis gesetzt auf: {BASE}")

LOG = BASE / "auto_gatekeeper_log.txt"
DESKTOP = Path.home() / "Desktop"
ERROR_COPY = DESKTOP / "Gatekeeper_FEHLER.txt"
PROCESS_REPORT = BASE / "process_report.json"
KODA_FILE = BASE / "KonDa_Final.txt"
HS_FILE = BASE / "HS_Final.txt"
HS_EMBED_FILE = BASE / "HS_Final_embedded_v3.py"
KEYS_OUT = BASE / "keys_out.json"
TOOLS = BASE / "Tools"

# Erwartete Dateien nach jedem Schritt
EXPECTED_FILES = {
    "handshake_v4.py": "handshake_report.json",
    "derive_keys_v1.py": "keys_out.json",
    "integrity_snapshot.py": "integrity_baseline.json",
    "verify_integrity.py": "verify_report.json",
    "embed_starter_into_hs_v3.py": "HS_Final_embedded_v3.py"
}

# ======================================================
# 🧠 Hilfsfunktionen
# ======================================================

def log(msg: str):
    """Schreibt Nachricht mit Zeitstempel ins Log (anhängend)."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a", encoding="utf-8", errors="ignore") as f:
        f.write(f"[{stamp}] {msg}\n")


def derive_fallback_key():
    """Erstellt eine Dummy keys_out.json, falls Ableitung fehlschlägt."""
    dummy_key = hashlib.sha256(b"Elaris_Fallback_Key").hexdigest()
    dummy_data = {
        "dummy_key": dummy_key,
        "note": "Fallback-Key automatisch erzeugt – derive_keys_v1.py fehlgeschlagen oder leer"
    }
    with open(KEYS_OUT, "w", encoding="utf-8") as f:
        json.dump(dummy_data, f, indent=2, ensure_ascii=False)
    log("[FALLBACK] keys_out.json automatisch mit Dummy-Key erstellt.")
    print("[FALLBACK] keys_out.json automatisch mit Dummy-Key erstellt.")


def run_python(script_path: Path):
    """Führt ein Python-Skript aus und protokolliert es."""
    if not script_path.exists():
        log(f"[WARN] {script_path.name} fehlt ({script_path})")
        return False

    log(f"▶️ Starte {script_path.name}")
    result = subprocess.run(
        ["python", str(script_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )

    if result.stdout.strip():
        with open(LOG, "a", encoding="utf-8", errors="ignore") as f:
            f.write(result.stdout + "\n")

    if result.returncode == 0:
        log(f"✅ {script_path.name} abgeschlossen.")
        return True
    else:
        err_msg = result.stderr.strip() or "Unbekannter Fehler"
        log(f"❌ {script_path.name} Fehler: {err_msg}")
        return False


# ======================================================
# 🧩 HS + KoDa Embed-Prüfung
# ======================================================

def check_and_repair_embeds():
    """Prüft HS und KoDa auf Embed-Blöcke und repariert sie bei Bedarf."""
    # ---- KoDa prüfen ----
    if not KODA_FILE.exists():
        log("[ERROR] KonDa_Final.txt fehlt vollständig!")
    else:
        content = KODA_FILE.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"#⟐KODA-ZW-BEGIN[\s\S]+?#⟐KODA-ZW-END", content):
            log("[OK] KoDa Embed-Block vorhanden.")
        else:
            log("[FIX] Kein Embed in KoDa_Final.txt – Reparatur...")
            repair_script = TOOLS / "embed_starter_into_koda_v3.py"
            if repair_script.exists():
                subprocess.run(["python", str(repair_script)])
                log("[OK] KoDa repariert.")
            else:
                log("[WARN] embed_starter_into_koda_v3.py fehlt.")

    # ---- HS prüfen ----
    if not HS_FILE.exists():
        log("[ERROR] HS_Final.txt fehlt vollständig!")
    else:
        if not HS_EMBED_FILE.exists():
            log("[FIX] HS_Final_embedded_v3.py fehlt – Versuch Reparatur...")
            hs_script = TOOLS / "embed_starter_into_hs_v3.py"
            if hs_script.exists():
                subprocess.run(["python", str(hs_script)])
                log("[OK] HS Embed neu erstellt.")
            else:
                log("[WARN] embed_starter_into_hs_v3.py fehlt – HS Embed konnte nicht erzeugt werden.")
        else:
            log("[OK] HS Embed-Datei vorhanden.")


# ======================================================
# 🧠 Hauptablauf
# ======================================================

def main():
    LOG.write_text("", encoding="utf-8")
    log("=== Elaris Auto-Gatekeeper gestartet ===")

    # 🔍 Embed-Prüfung
    check_and_repair_embeds()

    # Tools-Pfade für die Hauptmodule
    tool_steps = [
        TOOLS / "handshake_v4.py",
        TOOLS / "derive_keys_v1.py",
        TOOLS / "integrity_snapshot.py",
        TOOLS / "verify_integrity.py"
    ]

    ok_count = 0
    for step in tool_steps:
        if run_python(step):
            ok_count += 1
        elif step.name == "derive_keys_v1.py" and not KEYS_OUT.exists():
            log("[FALLBACK] keys_out.json wurde nicht erstellt – Fallback-Key wird erzeugt.")
            derive_fallback_key()

    # 🧠 Nachverfolgung: Erstellte Dateien prüfen
    missing_files = []
    for script, file_name in EXPECTED_FILES.items():
        file_path = BASE / file_name
        if not file_path.exists():
            cause = "Datei wurde nicht erstellt – möglicher Fehler im Script oder fehlende Quelle"
            if "HS" in file_name:
                cause = "HS Embed-Datei fehlt – möglicherweise wurde embed_starter_into_hs_v3.py nicht ausgeführt"
            missing_files.append({
                "file": file_name,
                "expected_by": f"Tools/{script}",
                "possible_cause": cause
            })

    # 🧾 Prozessbericht schreiben
    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "✅ OK" if not missing_files else "❌ Unvollständig",
        "missing_files": missing_files,
        "summary": {
            "expected": len(EXPECTED_FILES),
            "created": len(EXPECTED_FILES) - len(missing_files),
            "missing": len(missing_files)
        }
    }
    with open(PROCESS_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    if missing_files:
        log("[WARN] Prozessbericht erstellt – fehlende Dateien erkannt.")
    else:
        log("[OK] Prozessbericht vollständig – alle Dateien vorhanden.")

    # 🧠 Endauswertung
    if ok_count == len(tool_steps) and not missing_files:
        log("🧠 Gesamtergebnis: ✅ OK – Alle Module erfolgreich.")
    else:
        log(f"⚠️ Gesamtergebnis: Teilweise Fehler ({ok_count}/{len(tool_steps)})")

    log("=== Lauf beendet ===")

    # ======================================================
    # 🔔 Desktop-Benachrichtigung (stabilisiert)
    # ======================================================
    def show_toast_safely(title, message, duration=8):
        """Threaded, um GUI-Blocking und WNDPROC-Fehler zu verhindern."""
        try:
            from win10toast_click import ToastNotifier
            toast = ToastNotifier()
            threading.Thread(target=lambda: toast.show_toast(title, message, duration=duration, threaded=True), daemon=True).start()
        except Exception:
            try:
                from win10toast import ToastNotifier
                toast = ToastNotifier()
                threading.Thread(target=lambda: toast.show_toast(title, message, duration=duration, threaded=True), daemon=True).start()
            except Exception as e:
                log(f"[WARN] Toast konnte nicht angezeigt werden: {e}")

    title = "Elaris Systemüberprüfung"
    if not missing_files:
        msg = "Integritätsprüfung erfolgreich – alle Module OK ✅"
    else:
        msg = f"Gatekeeper-Warnung: {len(missing_files)} Datei(en) fehlen ⚠️"
        try:
            shutil.copy(LOG, ERROR_COPY)
            log(f"[INFO] Fehlerlog auf Desktop exportiert: {ERROR_COPY}")
        except Exception as copy_err:
            log(f"[WARN] Fehler beim Exportieren des Fehlerlogs: {copy_err}")

    show_toast_safely(title, msg)
    log(f"[INFO] Desktop-Toast gesendet: {msg}")


# ======================================================
# 🔚 MAIN
# ======================================================

if __name__ == "__main__":
    main()
