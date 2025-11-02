# 🔓 unlock_baseline.py
# Funktion: Hebt den Baseline-Lock nur mit gültigem Notfall-Hash auf.
# Sicherheitsstufe: Level 5 (Autorisierter Entsperrvorgang)
# Erstellt: 2025-09-27

import json
import hashlib
from pathlib import Path
from datetime import datetime

# ==========================================================
# 🔹 Hilfsfunktionen
# ==========================================================

def sha256_hex(data: str) -> str:
    """Berechnet SHA256-Hash eines Strings."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def verify_notfall_key_hash(input_hash: str, keys_path: Path) -> bool:
    """
    Prüft, ob der eingegebene Hash zum gespeicherten Notfall-Key passt.
    Akzeptiert vollständigen oder verkürzten (12 Zeichen) Hash.
    """
    if not keys_path.exists():
        print("❌ Schlüsseldatei keys_out.json nicht gefunden.")
        return False

    try:
        keys = json.loads(keys_path.read_text(encoding="utf-8"))
        notfall_key = keys.get("notfall")
        if not notfall_key:
            print("❌ Kein Notfallschlüssel gefunden.")
            return False

        full_hash = sha256_hex(notfall_key)
        short_hash = full_hash[:12]

        if input_hash == full_hash or input_hash == short_hash:
            print("✅ Notfall-Hash verifiziert.")
            return True
        else:
            print("❌ Ungültiger Hash oder Prüfsumme.")
            print("💡 Tipp: Gib den vollständigen SHA256-Hash oder die ersten 12 Zeichen ein.")
            return False
    except Exception as e:
        print("[ERROR] Fehler beim Verifizieren:", e)
        return False


# ==========================================================
# 🔸 Hauptfunktion
# ==========================================================

def unlock_baseline():
    base = Path.cwd()
    lock_path = base / "baseline.lock"
    keys_path = base / "keys_out.json"

    if not lock_path.exists():
        print("ℹ️ Kein Lock gefunden – nichts zu entsperren.")
        return

    print("🔒 Aktueller Lock erkannt.")
    print("🔑 Bitte autorisieren Sie den Entsperrvorgang mit dem Notfall-Hash:")
    user_input = input("👉 Eingabe (12 Zeichen oder voller Hash): ").strip().lower()

    if not verify_notfall_key_hash(user_input, keys_path):
        print("❌ Zugriff verweigert – Lock bleibt bestehen.")
        return

    try:
        lock_path.unlink()
        print("\n✅ Lock erfolgreich entfernt.")
        print(f"🕒 Zeit: {datetime.utcnow().isoformat()}Z")
        print("🧠 Autorisierung über sicheren Notfall-Hash bestätigt.")
    except Exception as e:
        print("❌ Fehler beim Entfernen des Lock-Files:", e)


# ==========================================================
# 🔹 Main Entry
# ==========================================================

if __name__ == "__main__":
    unlock_baseline()
