# 🧩 Secure Baseline Reset (v3) – Hash-basierte Notfallprüfung mit Rücksprung ins GUI
# Erstellt: 2025-09-27
# Sicherheitsstufe: Level 5 (Hochsicher-Reset + GUI-Reintegration)

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

# =====================================================
# 🔹 Hilfsfunktionen
# =====================================================

def sha256_hex(data: str) -> str:
    """SHA256-Hash für beliebigen String"""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def file_hash(path: Path) -> str:
    """Berechnet SHA256 einer Datei (UTF-8)"""
    try:
        content = path.read_text(encoding="utf-8")
        return sha256_hex(content)
    except Exception as e:
        print(f"[ERROR] Datei konnte nicht gelesen werden: {path.name} – {e}")
        return None


def verify_notfall_key_hash(input_hash: str, keys_path: Path) -> bool:
    """Verifiziert den eingegebenen SHA256-Hash gegen den gespeicherten Notfall-Key."""
    if not keys_path.exists():
        print("❌ Schlüsseldatei nicht gefunden! Bitte derive_keys_v1.py ausführen.")
        return False

    try:
        keys = json.loads(keys_path.read_text(encoding="utf-8"))
        notfall_key = keys.get("notfall")
        if not notfall_key:
            print("❌ Kein Notfallschlüssel in keys_out.json gefunden.")
            return False

        stored_hash = sha256_hex(notfall_key)
        short_hash = stored_hash[:12]

        if input_hash == stored_hash or input_hash == short_hash:
            print("✅ Notfallschlüssel-Hash verifiziert.")
            return True
        else:
            print("❌ Ungültiger Hash oder Prüfsumme.")
            print("💡 Tipp: Gib entweder den vollständigen SHA256-Hash oder die ersten 12 Zeichen ein.")
            return False
    except Exception as e:
        print("[ERROR] Schlüsselprüfung fehlgeschlagen:", e)
        return False


def write_baseline(hs_hash: str, koda_hash: str, out_path: Path):
    """Schreibt neue Integritätsbaseline"""
    baseline_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "trusted_hashes": {
            "HS_Final": hs_hash,
            "KoDa_Final": koda_hash
        }
    }
    out_path.write_text(json.dumps(baseline_data, indent=2, ensure_ascii=False), encoding="utf-8")

# =====================================================
# 🔸 Hauptfunktion
# =====================================================

def reset_secure_baseline():
    base = Path.cwd()
    hs_path = base / "HS_Final.txt"
    koda_path = base / "KonDa_Final.txt"
    keys_path = base / "keys_out.json"
    baseline_path = base / "integrity_baseline.json"
    lock_path = base / "baseline.lock"
    gui_path = base / "lock_console_gui.py"

    # Prüfung: Dateien vorhanden?
    if not hs_path.exists() or not koda_path.exists():
        print("❌ Fehlende HS_Final.txt oder KonDa_Final.txt.")
        return

    # Lock prüfen
    if lock_path.exists():
        print("🔒 Baseline ist gesperrt. Nur autorisierter Reset mit Notfall-Hash möglich.")
    else:
        print("[INFO] Kein Lock vorhanden – erster autorisierter Reset wird durchgeführt.")

    # Eingabe
    print("\n🔑 Bitte den SHA256-Hash ODER die ersten 12 Zeichen des Hashes des Notfallschlüssels eingeben:")
    user_hash = input("👉 Hash-Eingabe: ").strip().lower()

    if not verify_notfall_key_hash(user_hash, keys_path):
        print("❌ Zugriff verweigert – Reset wird abgebrochen.")
        return

    # Hashes berechnen
    hs_hash = file_hash(hs_path)
    koda_hash = file_hash(koda_path)

    # Neue Baseline schreiben
    write_baseline(hs_hash, koda_hash, baseline_path)

    # Lockdatei setzen
    lock_data = {
        "locked": True,
        "created": datetime.utcnow().isoformat() + "Z",
        "authorized_by": "Notfall-Hash",
        "hash_used": user_hash
    }
    lock_path.write_text(json.dumps(lock_data, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n✅ Neue Integritäts-Baseline erfolgreich gesetzt.")
    print(f"📄 {baseline_path}")
    print(f"🔒 Lock erstellt: {lock_path}")
    print("🧠 Authentifizierung über sicheren Hash-Eingang abgeschlossen.")

    # Nach Abschluss GUI wieder öffnen
    if gui_path.exists():
        print("\n🧠 Starte Elaris Lock-Konsole zur Verifikation...")
        subprocess.Popen(["python", str(gui_path)], shell=True)
    else:
        print("\n⚠️ GUI-Konsole (lock_console_gui.py) nicht gefunden. Bitte manuell starten.")

# =====================================================
# 🔹 Main Entry
# =====================================================

if __name__ == "__main__":
    reset_secure_baseline()
