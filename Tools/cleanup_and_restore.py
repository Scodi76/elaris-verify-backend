# 🧹 Gatekeeper Cleanup & Restore Tool v1.1 (UTF-safe)
# Korrigiert: Umbenennung erst nach vollständiger Löschung
# Sicherheitsstufe: 5

import os
import json
import shutil
from pathlib import Path
import subprocess

BASE = Path.cwd()

DELETE_FILES = [
    "process_report.json",
    "handshake_report.json",
    "verify_report.json",
    "RAM_PROOF.json",
    "integrity_baseline.json",
    "baseline.lock",
    "keys_out.json",
    "HS_Final.txt",
    "KonDa_Final.txt"
]

RENAME_FILES = {
    "HS_Final_first.txt": "HS_Final.txt",
    "KonDa_Final_first.txt": "KonDa_Final.txt"
}

# ==========================================================
# 🔹 Hilfsfunktionen
# ==========================================================

def safe_delete(file):
    """Sichere Löschung mit Rückmeldung"""
    path = BASE / file
    if path.exists():
        try:
            path.unlink()
            print(f"[🗑] {file} gelöscht.")
        except Exception as e:
            print(f"[⚠️] Fehler beim Löschen von {file}: {e}")
    else:
        print(f"[ℹ️] {file} nicht vorhanden – übersprungen.")

def safe_rename(src, dest):
    """Umbenennen, falls vorhanden"""
    src_path = BASE / src
    dest_path = BASE / dest
    if not src_path.exists():
        print(f"[❌] {src} nicht gefunden – kann nicht umbenannt werden.")
        return
    if dest_path.exists():
        print(f"[⚠️] {dest} existiert bereits – wird übersprungen.")
        return
    try:
        shutil.copy2(src_path, dest_path)
        print(f"[✅] {src} → {dest} wiederhergestellt.")
    except Exception as e:
        print(f"[❌] Fehler beim Umbenennen {src}: {e}")

def all_deleted():
    """Prüft, ob alle relevanten Dateien wirklich entfernt sind"""
    remaining = [f for f in DELETE_FILES if (BASE / f).exists()]
    if remaining:
        print("\n⚠️ Folgende Dateien konnten nicht gelöscht werden:")
        for r in remaining:
            print("   -", r)
        return False
    return True

# ==========================================================
# 🔹 Hauptablauf
# ==========================================================

def main():
    print("🧹 Elaris Gatekeeper Cleanup & Restore Tool (v1.1)")
    print("--------------------------------------------------")
    confirm = input("⚠️  Willst du wirklich den kompletten Reset durchführen? (ja/nein): ").strip().lower()
    if confirm not in ("ja", "j"):
        print("❌ Abbruch – keine Änderungen vorgenommen.")
        return

    print("\n🔍 Lösche alte Hash-, Report- und Schlüsseldateien...\n")
    for f in DELETE_FILES:
        safe_delete(f)

    # 🧠 Prüfen, ob wirklich alles gelöscht wurde
    if not all_deleted():
        print("\n❌ Umbenennung abgebrochen – nicht alle Dateien gelöscht.")
        return

    print("\n🧩 Wiederherstellen der Ursprungsdateien...\n")
    for src, dest in RENAME_FILES.items():
        safe_rename(src, dest)

    print("\n✅ Reset erfolgreich abgeschlossen.")
    print("🔄 Gatekeeper ist nun bereit für einen neuen vollständigen Lauf.\n")

    run_next = input("🚀 Soll jetzt automatisch 'run_gatekeeper_full.py' gestartet werden? (ja/nein): ").strip().lower()
    if run_next in ("ja", "j"):
        subprocess.run(["python", "run_gatekeeper_full.py"], shell=True)
    else:
        print("🧠 Hinweis: Du kannst den Lauf später manuell starten mit:\n   python run_gatekeeper_full.py")

# ==========================================================
# 🔸 Einstiegspunkt
# ==========================================================

if __name__ == "__main__":
    main()
