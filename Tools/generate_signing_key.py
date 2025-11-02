# 🧠 Elaris – Signaturschlüssel-Generator
# Erzeugt eine neue signing_key.json mit einem zufälligen SHA256-Hex-Schlüssel.
# Version: 1.0

import os
import json
import hashlib
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent
KEY_FILE = BASE / "signing_key.json"

def generate_random_key():
    """Erzeugt 32 zufällige Bytes und gibt sie als Hex-String zurück."""
    random_bytes = os.urandom(32)
    return hashlib.sha256(random_bytes).hexdigest().upper()

def main():
    print("🔐 Erzeuge neuen kryptografischen Signaturschlüssel...\n")

    if KEY_FILE.exists():
        print(f"⚠️  Es existiert bereits eine Datei: {KEY_FILE.name}")
        choice = input("Möchtest du sie überschreiben? (j/n): ").strip().lower()
        if choice != "j":
            print("🚫 Vorgang abgebrochen. Alte Schlüsseldatei bleibt erhalten.")
            return

    private_key_hex = generate_random_key()
    data = {
        "type": "sha256-hex",
        "private_key_hex": private_key_hex
    }

    try:
        BASE = Path(__file__).parent
        key_path = BASE / "signing_key.json"

        with open(key_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ Neuer Signierschlüssel gespeichert unter: {key_path}")
        print(f"🔑 Hash: {private_key_hex[:16]}... (verkürzt angezeigt)")

    except Exception as e:
        print(f"❌ Fehler beim Speichern der Schlüsseldatei: {e}")

if __name__ == "__main__":
    main()
