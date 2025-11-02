import json
import os
import getpass
import secrets
import hashlib

def derive_key_from_passphrase(passphrase: str) -> str:
    # SHA256 über Passphrase für deterministischen Key
    return hashlib.sha256(passphrase.encode('utf-8')).hexdigest()

def main():
    print("🔐 ELARIS: Signatur-Schlüssel-Erstellung")
    passphrase = getpass.getpass("Bitte gib eine Passphrase ein (unsichtbar): ")

    private_key_hex = derive_key_from_passphrase(passphrase)
    public_key_hex = hashlib.sha256(bytes.fromhex(private_key_hex)).hexdigest()

    key_data = {
        "type": "elaris-sign-key",
        "private_key_hex": private_key_hex,
        "public_key_hex": public_key_hex,
        "created_by": "set_passphrase.py",
        "created_at": __import__('datetime').datetime.utcnow().isoformat() + "Z"
    }

    out_path = os.path.join(os.getcwd(), "signing_key.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(key_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Schlüsseldatei erfolgreich erstellt: {out_path}")

if __name__ == "__main__":
    main()
