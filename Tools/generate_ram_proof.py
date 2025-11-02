
import json
import secrets
from pathlib import Path

def generate_ram_proof(output_path="RAM_PROOF.json", session_id="default-session"):
    key = secrets.token_bytes(32)
    ram_proof = {
        "session_id": session_id,
        "key": key.hex()
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ram_proof, f, indent=2)
    print(f"RAM_PROOF saved to {output_path}")

# Beispiel: starten mit
# generate_ram_proof("RAM_PROOF.json", "elaris-upload-session-2025")
if __name__ == "__main__":
    generate_ram_proof()
