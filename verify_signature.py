import json
import hashlib
from pathlib import Path
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import base64
import sys

def verify_signature(file_path, signature_json_path):
    # Datei einlesen und SHA256 berechnen
    file_data = Path(file_path).read_bytes()
    digest = hashlib.sha256(file_data).hexdigest()

    # Signaturdatei laden
    with open(signature_json_path, "r", encoding="utf-8") as f:
        sig_data = json.load(f)

    expected_digest = sig_data["digest_sha256_hex"]
    signature = base64.b64decode(sig_data["signature_base64"])
    public_key_bytes = bytes.fromhex(sig_data["public_key_hex"])

    # Digest vergleichen
    if digest != expected_digest:
        print("❌ Datei-Hash stimmt NICHT mit der Signaturdatei überein.")
        return False

    # Verifikation
    try:
        verify_key = VerifyKey(public_key_bytes)
        verify_key.verify(digest.encode(), signature)
        print("✅ Digitale Signatur ist gültig.")
        print("✅ Datei ist authentisch und wurde nicht verändert.")
        return True
    except BadSignatureError:
        print("❌ Signatur ungültig – Datei wurde manipuliert oder falscher Schlüssel.")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Verwendung:\n  python verify_signature.py <dateipfad> <signaturdatei>")
        sys.exit(1)

    file_path = sys.argv[1]
    signature_path = sys.argv[2]
    verify_signature(file_path, signature_path)
