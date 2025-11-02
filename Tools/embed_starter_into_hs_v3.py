# 🔐 embed_starter_into_hs_v3.8 – UTF-safe & Auto-Repair-ready
# Zero-Width + Sichtbarer Fallback-Metablock + Sicherer Reparaturmodus
# Voll kompatibel mit Windows-Terminal (CP1252)
# Keine Emoji-Ausgabe → stabil für Auto-Gatekeeper

from pathlib import Path
import hashlib
import base64
from cryptography.fernet import Fernet
import re
import string
import json
import hmac
import shutil
import os
import sys

# Reparaturmodus prüfen
IS_REPAIR_MODE = "--no-handshake" in sys.argv

# Terminalkompatibilität prüfen
USE_ASCII = False
try:
    "→".encode(sys.stdout.encoding or "utf-8")
except Exception:
    USE_ASCII = True

def arrow():
    return "->" if USE_ASCII else "→"

# ===========================================================
# 🔹 Hilfsfunktionen
# ===========================================================

def extract_stylometrics(text):
    lines = text.splitlines()
    return {
        "char_count": sum(len(line) for line in lines),
        "line_count": len(lines),
        "comment_line_count": sum(1 for line in lines if line.strip().startswith("#")),
        "empty_line_count": sum(1 for line in lines if not line.strip()),
        "uppercase_ratio": round(sum(1 for c in text if c.isupper()) / max(1, sum(1 for c in text if c.islower())), 4),
        "punctuation_count": sum(1 for c in text if c in string.punctuation)
    }

def encode_zero_width(input_string):
    mapping = {'0': '\u200b', '1': '\u200c'}
    binary = ''.join(f"{ord(c):08b}" for c in input_string)
    return ''.join(mapping[b] for b in binary)

def compute_hmac(content: str, session_id: str, ram_path="RAM_PROOF.json"):
    try:
        ram = json.loads(Path(ram_path).read_text(encoding="utf-8"))
        key = bytes.fromhex(ram["key"])
        message = f"{session_id}:{content}".encode()
        return hmac.new(key, message, hashlib.sha256).hexdigest()
    except Exception as e:
        print(f"[WARN] RAM_PROOF.json nicht lesbar oder fehlerhaft: {e}")
        return "NO_HMAC"

# ===========================================================
# 🔸 Hauptfunktion
# ===========================================================

def embed_starter_into_hs(source_file, start_file, output_file, passphrase, ram_proof="RAM_PROOF.json"):
    # Start-ID extrahieren
    start_text = Path(start_file).read_text(encoding="utf-8", errors="ignore")
    start_id = None
    for line in start_text.splitlines():
        match = re.search(r"GATE:START_ID:\s*([\w\-]+)", line)
        if match:
            start_id = match.group(1)
            break

    if not start_id:
        print("[WARN] START_ID nicht gefunden – Standard-ID wird verwendet.")
        start_id = "DEFAULT-SESSION-ID"

    content = Path(source_file).read_text(encoding="utf-8", errors="ignore")

    # Stylometrie + Hash
    metrics = extract_stylometrics(content)
    sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    combined = f"{sha256}:{start_id}"
    starter_hash = hashlib.sha256(combined.encode()).hexdigest()

    # Fernet-Schlüssel generieren
    fernet_key = base64.urlsafe_b64encode(hashlib.sha256(passphrase.encode()).digest()[:32])
    f = Fernet(fernet_key)
    encrypted = f.encrypt(starter_hash.encode()).decode()

    # HMAC berechnen
    hmac_digest = compute_hmac(content, start_id, ram_proof)

    build_meta = {
        "v": "3.8",
        "type": "build-meta",
        "sha256": sha256,
        "hmac": hmac_digest,
        "metrics": metrics
    }

    # Zero-Width + sichtbarer Block
    zw_block = encode_zero_width(json.dumps(build_meta, separators=(',', ':')))
    visible_meta = (
        "#HS-META-BEGIN\n"
        + json.dumps(build_meta, indent=2, ensure_ascii=False)
        + "\n#HS-META-END\n"
    )

    # Grundinhalt zusammenbauen
    result = (
        content.rstrip()
        + "\n\n#HS-ZW-BEGIN\n"
        + zw_block
        + "\n#HS-ZW-END\n"
        + visible_meta
        + "\n"
    )

    # ===========================================================
    # 🧩 Cross-Link-Header automatisch einfügen
    # ===========================================================
    crosslink_header = (
        "# =========================================\n"
        "# Cross-Link-Reference: KoDa_Final_embedded_v3\n"
        "# Hinweis:\n"
        "# Diese HS-Version ist mit der Konsolidierungsdatei KoDa_Final_embedded_v3 verknüpft.\n"
        "# Der Cross-Link dient der Integritätsprüfung zwischen HS und KoDa.\n"
        "# =========================================\n\n"
    )

    full_output = crosslink_header + result

    # Debug
    print("[DEBUG] Cross-Link-Header eingebettet.")
    print("[DEBUG] Zero-Width-Block-Länge:", len(zw_block))
    print("[DEBUG] Erste 80 Zeichen (sichtbar ersetzt):",
          zw_block[:80].replace('\u200b', '0').replace('\u200c', '1'))

    # Backup
    original_path = Path("HS_Final.txt")
    backup_path = Path("HS_Final_first.txt")
    if original_path.exists():
        print(f"[INFO] Backup: HS_Final.txt {arrow()} HS_Final_first.txt")
        shutil.copy2(original_path, backup_path)
        print("[OK] Backup gespeichert:", backup_path.name)

    # Schreiben
    Path("HS_Final.txt").write_text(full_output, encoding="utf-8")
    Path(output_file).write_text(full_output, encoding="utf-8")
    print("[OK] Cross-Link + Zero-Width + Meta erfolgreich eingebettet.")

# ===========================================================
# 🧠 Main Entry
# ===========================================================

if __name__ == "__main__":
    original = Path("HS_Final.txt")
    embedded = Path("HS_Final_embedded_v3.py")

    if not original.exists():
        raise FileNotFoundError("HS_Final.txt wurde nicht gefunden!")

    print(f"[INFO] Backup: HS_Final.txt {arrow()} HS_Final_first.txt")
    shutil.copy2(original, Path("HS_Final_first.txt"))

    embed_starter_into_hs(
        str(original),
        "Start_final.txt",
        str(embedded),
        "ElarisTestPassphrase2025!",
        "RAM_PROOF.json"
    )

    # Reparaturmodus sofort beenden
    if IS_REPAIR_MODE:
        print("[INFO] Reparaturmodus aktiv – Handshake & Schlüsselableitung werden übersprungen.")
        sys.exit(0)

    # Nur im Normalmodus
    print("[AUTO] Starte handshake.py ...")
    os.system("python handshake.py")
    print("[OK] Handshake abgeschlossen.")

    print("[AUTO] Starte derive_keys_v1.py ...")
    os.system("python derive_keys_v1.py")
    print("[OK] Schlüsseldatei erstellt.")
