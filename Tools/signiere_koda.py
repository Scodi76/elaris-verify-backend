# ======================================================
# Signaturmodul – KoDa-Version (rein ASCII, UTF-8-kompatibel)
# ======================================================

import json
import hashlib
import hmac
import sys
import io
import os
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
    """Erstellt eine HMAC-SHA256-Signatur für KoDa_Final.txt und bettet bei Bedarf einen Notfallschlüssel ein."""
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

    # Dateiinhalt binär lesen (für HMAC)
    with open(file_path, "rb") as f:
        content = f.read()

    # Notfallschlüssel prüfen / einbetten
    try:
        with open(file_path, "r", encoding="utf-8") as fr:
            text_content = fr.read()

        if "# === SYSREF_GUID ===" not in text_content:
            emergency_key = hashlib.sha256(os.urandom(32)).hexdigest().upper()
            emergency_block = (
                "\n\n# === SYSREF_GUID ===\n"
                f"SHA256: {emergency_key}\n"
                "# === SYSREF_END ===\n"
            )
            text_content += emergency_block

            with open(file_path, "w", encoding="utf-8") as fw:
                fw.write(text_content)

            safe_print("[INFO] Notfallschlüssel (SYSREF_GUID) wurde eingebettet.")
        else:
            safe_print("[INFO] Notfallschlüssel bereits vorhanden – kein neuer erstellt.")
    except Exception as e:
        safe_print(f"[WARN] Fehler beim Einbetten des Notfallschlüssels: {e}")

    # HMAC-Signatur erzeugen
    signature = hmac.new(private_key_bytes, content, hashlib.sha256).hexdigest()

    # Signaturdaten speichern
    sig_data = {
        "file": str(file_path),
        "signature": signature,
        "hash_algorithm": "SHA256",
        "method": "HMAC",
        "key_type": key_data.get("type", "sha256-hex"),
        "created_at": datetime.utcnow().isoformat() + "Z"
    }

    out_path = file_path.with_suffix(file_path.suffix + ".signature.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(sig_data, f, indent=2, ensure_ascii=False)

    safe_print(f"[OK] Signatur erfolgreich erstellt: {out_path}")


if __name__ == "__main__":
    try:
        sign_file("KonDa_Final.txt", "signing_key.json")
    except Exception as e:
        safe_print(f"[ERROR] {e}")
        sys.exit(1)
