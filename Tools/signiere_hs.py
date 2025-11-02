# ======================================================
# Signaturmodul – HS-Version (rein ASCII, UTF-8-kompatibel)
# ======================================================

import json
import hashlib
import hmac
import sys
import io
from pathlib import Path
from datetime import datetime

# UTF-8-Ausgabe in Windows-Konsole erzwingen
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

def safe_print(*args, **kwargs):
    """Unicode-sichere, ASCII-kompatible Konsolenausgabe"""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        clean_args = [str(a).encode('utf-8', errors='replace').decode('utf-8') for a in args]
        print(*clean_args, **kwargs)


def sign_file(file_path: str, key_path: str):
    """Erstellt eine HMAC-SHA256-Signatur für die angegebene Datei."""
    file_path = Path(file_path)
    key_path = Path(key_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")
    if not key_path.exists():
        raise FileNotFoundError(f"Schlüsseldatei nicht gefunden: {key_path}")

    # Schlüssel laden
    with open(key_path, "r", encoding="utf-8") as f:
        key_data = json.load(f)

    if "private_key_hex" not in key_data:
        raise ValueError("Ungültiger Schlüssel: Feld 'private_key_hex' fehlt")

    private_key_hex = key_data["private_key_hex"]
    private_key_bytes = bytes.fromhex(private_key_hex)

    # Dateiinhalt laden
    with open(file_path, "rb") as f:
        content = f.read()

    # HMAC mit SHA256 erzeugen
    signature = hmac.new(private_key_bytes, content, hashlib.sha256).hexdigest()

    # Signatur-Objekt vorbereiten
    sig_data = {
        "file": str(file_path),
        "signature": signature,
        "hash_algorithm": "SHA256",
        "method": "HMAC",
        "key_type": key_data.get("type", "sha256-hex"),
        "created_at": datetime.utcnow().isoformat() + "Z"
    }

    # Signaturdatei schreiben
    out_path = file_path.with_suffix(file_path.suffix + ".signature.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(sig_data, f, indent=2, ensure_ascii=False)

    safe_print(f"[OK] Signatur erfolgreich erstellt: {out_path}")


if __name__ == "__main__":
    try:
        sign_file("HS_Final.txt", "signing_key.json")
    except Exception as e:
        safe_print(f"[ERROR] {e}")
        sys.exit(1)
