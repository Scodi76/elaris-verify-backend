# 🧭 lock_status.py
# Funktion: Zeigt den aktuellen Status des Baseline-Locks an
# Erstellt: 2025-09-27
# Sicherheitsstufe: Level 5 – Nur Lesezugriff, keine Änderungen

import json
from pathlib import Path
from datetime import datetime

def show_lock_status():
    base = Path.cwd()
    lock_path = base / "baseline.lock"
    baseline_path = base / "integrity_baseline.json"

    print("🔍 Prüfe aktuellen Baseline-Lock-Status...\n")

    # 1️⃣ Prüfen, ob Lock-Datei existiert
    if not lock_path.exists():
        print("✅ Kein Lock aktiv – Baseline ist frei und beschreibbar.")
    else:
        try:
            lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
            created = lock_data.get("created", "Unbekannt")
            authorized_by = lock_data.get("authorized_by", "Unbekannt")
            hash_used = lock_data.get("hash_used", "—")

            print("🔒 Lock ist aktiv!")
            print(f"🕒 Erstellt am: {created}")
            print(f"👤 Autorisiert durch: {authorized_by}")
            print(f"🔑 Hash (gekürzt): {hash_used[:12]}...")
        except Exception as e:
            print("❌ Fehler beim Lesen der Lock-Datei:", e)

    # 2️⃣ Prüfen, ob Baseline-Datei vorhanden ist
    if baseline_path.exists():
        try:
            baseline_data = json.loads(baseline_path.read_text(encoding="utf-8"))
            ts = baseline_data.get("timestamp", "Unbekannt")
            trusted = baseline_data.get("trusted_hashes", {})
            print("\n📘 Aktuelle Baseline:")
            print(f"   🕒 Zeitstempel: {ts}")
            print(f"   🔹 HS_Final: {trusted.get('HS_Final', '—')[:12]}...")
            print(f"   🔹 KoDa_Final: {trusted.get('KoDa_Final', '—')[:12]}...")
        except Exception as e:
            print("❌ Fehler beim Lesen der Baseline-Datei:", e)
    else:
        print("\n⚠️ Keine Baseline gefunden – möglicherweise noch nicht erstellt.")

    print("\n✅ Statusprüfung abgeschlossen.")


if __name__ == "__main__":
    show_lock_status()
