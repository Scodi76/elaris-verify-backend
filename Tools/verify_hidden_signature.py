from nacl.signing import VerifyKey
from nacl.encoding import HexEncoder
import hashlib
import base64
import re

def decode_zero_width(zw_string):
    """Zero-Width-Encoded Base64 zurück zu lesbarem Base64"""
    mapping = {'\u200b': '0', '\u200c': '1'}
    bits = ''.join(mapping.get(c, '') for c in zw_string)
    chars = [chr(int(bits[i:i+8], 2)) for i in range(0, len(bits), 8)]
    return ''.join(chars)

def extract_hidden_signature(text):
    """Extrahiere die versteckte Zero-Width-Signaturzeile"""
    match = re.search(r"#⟐SIG-ZW: ([\u200b\u200c]+)", text)
    return match.group(1) if match else None

def verify_hidden_signature(file_path, public_key_hex):
    # Dateiinhalt laden
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Original ohne Signatur extrahieren
    content_lines = content.strip().splitlines()
    filtered_lines = [line for line in content_lines if not line.startswith("#⟐SIG-ZW:")]
    file_text_without_sig = '\n'.join(filtered_lines)

    # SHA256-Hash bilden
    digest = hashlib.sha256(file_text_without_sig.encode('utf-8')).hexdigest()

    # Zero-Width Signatur extrahieren
    zw_code = extract_hidden_signature(content)
    if not zw_code:
        print("❌ Keine versteckte Signaturzeile gefunden.")
        return

    try:
        signature_b64 = decode_zero_width(zw_code)
        signature_bytes = base64.b64decode(signature_b64)
    except Exception as e:
        print("❌ Fehler beim Decodieren der Signatur:", e)
        return

    # Verifikation mit öffentlichem Schlüssel
    try:
        verify_key = VerifyKey(public_key_hex, encoder=HexEncoder)
        verify_key.verify(digest.encode(), signature_bytes)
        print("✅ Versteckte Signatur ist GÜLTIG.")
        print(f"🔒 SHA256: {digest}")
    except Exception:
        print("❌ Versteckte Signatur ist UNGÜLTIG.")
        print(f"🔓 SHA256: {digest}")

# Beispiel-Anwendung
verify_hidden_signature("HS_Final.txt", "a5e9fc17a0aba26d08c7c74e8c48835ad809bb60cc0d49988c6bb4f06e7b2123")
