import json
import hashlib
import hmac
from pathlib import Path

def to_zero_width(binary_str):
    """Konvertiert eine Binärzeichenkette in Zero-Width-Zeichen."""
    mapping = {"0": "\u200B", "1": "\u200C"}
    return "".join(mapping[b] for b in binary_str)

def embed_hidden_signature(file_path, key_path):
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
    content = file_path.read_bytes()

    # Signatur (HMAC SHA256)
    signature = hmac.new(private_key_bytes, content, hashlib.sha256).digest()

    # In Binärstring umwandeln
    binary_str = "".join(f"{byte:08b}" for byte in signature)

    # Zero-Width encodieren
    zw_signature = to_zero_width(binary_str)

    # Zero-Width Block anhängen
    marker_start = "\n# === HIDDEN_SIGNATURE_START ===\n"
    marker_end = "\n# === HIDDEN_SIGNATURE_END ===\n"

    updated_content = content.decode("utf-8", errors="ignore") + marker_start + zw_signature + marker_end

    # Datei überschreiben
    file_path.write_text(updated_content, encoding="utf-8")

    print(f"✅ Versteckte Signatur erfolgreich eingebettet in: {file_path}")

if __name__ == "__main__":
    embed_hidden_signature("KonDa_Final.txt", "signing_key.json")
