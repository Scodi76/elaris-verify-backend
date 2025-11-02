# 🔐 derive_keys_v1.py – Elaris Key Derivation v2.1 (stabil & fehlertolerant)
# Erstellt: 2025-09-28
# Funktion: Leitet Schlüssel aus handshake_report.json ab + robustes Fallback

import json
import hashlib
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parents[2]  # geht 2 Ebenen hoch
HANDSHAKE_FILE = BASE / "handshake_report.json"
KEYS_OUT = BASE / "keys_out.json"
LOG_FILE = BASE / "auto_gatekeeper_log.txt"


def log(msg: str):
    """Eintrag ins Gatekeeper-Log (anhängend)."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8", errors="ignore") as f:
        f.write(f"[{stamp}] {msg}\n")

def derive_key(data: str, salt: str = "Elaris_Key_Derivation") -> str:
    """Leitet stabilen SHA256-Schlüssel aus Daten + Salt ab."""
    raw = (data + salt).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def flatten_values(obj):
    """Extrahiert rekursiv plausible Hash-Werte aus JSON-Objekt."""
    results = []
    if isinstance(obj, dict):
        for v in obj.values():
            results.extend(flatten_values(v))
    elif isinstance(obj, list):
        for v in obj:
            results.extend(flatten_values(v))
    elif isinstance(obj, str):
        # Nur plausible Hexstrings (mind. 16 Zeichen)
        if all(c in "0123456789abcdefABCDEF" for c in obj) and len(obj) >= 16:
            results.append(obj)
    return results

def main():
    log("=== Schlüsselableitung gestartet ===")

    if not HANDSHAKE_FILE.exists():
        print("[ERROR] handshake_report.json fehlt – Handshake nicht ausgeführt.")
        log("[ERROR] handshake_report.json fehlt – keine Schlüsselableitung möglich.")
        dummy = {"dummy_key": derive_key("fallback")}
        with open(KEYS_OUT, "w", encoding="utf-8") as f:
            json.dump(dummy, f, indent=2, ensure_ascii=False)
        print("[FALLBACK] keys_out.json mit Dummy-Key erstellt.")
        log("[FALLBACK] Dummy-Key erzeugt, um Prozessfluss aufrechtzuerhalten.")
        return

    # JSON laden
    with open(HANDSHAKE_FILE, "r", encoding="utf-8") as f:
        handshake_data = json.load(f)

    print("[INFO] handshake_report.json geladen.")
    log("[INFO] handshake_report.json geladen.")

    hashes = flatten_values(handshake_data)
    keys = {}

    if not hashes:
        print("[WARN] Keine Hash-Werte gefunden – Erzeuge Dummy-Key.")
        log("[WARN] Keine Hash-Werte gefunden, Erzeuge Dummy-Key.")
        keys["dummy_key"] = derive_key("fallback_sequence")
    else:
        print(f"[INFO] {len(hashes)} Hash-Werte extrahiert.")
        log(f"[INFO] {len(hashes)} Hash-Werte extrahiert.")

        for idx, val in enumerate(hashes, start=1):
            keys[f"hash_{idx:02d}"] = derive_key(val)

        combined = "".join(hashes)
        master_key = derive_key(combined, "Elaris_Master_Key")
        keys["master_key"] = master_key

    # Speichern
    with open(KEYS_OUT, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)

    if "dummy_key" in keys:
        print("[FALLBACK] keys_out.json mit Dummy-Key erzeugt.")
        log("[FALLBACK] keys_out.json mit Dummy-Key erzeugt.")
    else:
        print(f"[OK] keys_out.json erfolgreich erzeugt ({len(keys)} Schlüssel).")
        log(f"[OK] keys_out.json erfolgreich erzeugt ({len(keys)} Schlüssel).")

    log("=== Schlüsselableitung abgeschlossen ===")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[EXCEPTION] {e}")
        log(f"[EXCEPTION] {e}")
