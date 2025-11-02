# 🔐 Elaris Integrity Check v1.1
# Erstellt: 2025-09-27 | Überarbeitet: 2025-10-05
# Zweck: Überprüft HS_Final.txt auf Manipulation und repariert ggf. Zero-Width-Block
# Kompatibel mit: app_verify_backend_v5_9.py (Elaris Verify System)

import json
import re
import hashlib
from pathlib import Path
import shutil
from datetime import datetime

__version__ = "1.1"
__compatible_with__ = "app_verify_backend_v5_9"
__author__ = "Elaris Verify System"

# ==========================================================
# Hilfsfunktionen
# ==========================================================

def read_file(path: Path) -> str:
    """Liest den Inhalt einer Datei als UTF-8-Text ein."""
    return path.read_text(encoding="utf-8")

def strip_zero_chars(text: str) -> str:
    """Entfernt unsichtbare Steuerzeichen (Zero-Width, NBSP etc.)."""
    return re.sub(r"[\u200B-\u200F\u2060\uFEFF]", "", text)

def decode_visible_meta(content: str):
    """Liest sichtbaren Fallback-Metablock aus dem HS-Skript."""
    m = re.search(r"#⟐HS-META-BEGIN\s*(\{.*?\})\s*#⟐HS-META-END", content, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception as e:
        print("[ERROR] Sichtbarer Metablock fehlerhaft:", e)
        return None

def decode_zero_block(content: str):
    """Dekodiert Zero-Width-Block, falls vorhanden."""
    m = re.search(r"#⟐HS-ZW-BEGIN\s*([\u200B-\u200F\u2060\s]+?)#⟐HS-ZW-END", content, re.S)
    if not m:
        return None
    zw_raw = "".join(c for c in m.group(1) if c in "\u200b\u200c")
    if not zw_raw:
        return None
    bits = "".join("0" if c == "\u200b" else "1" for c in zw_raw)
    if len(bits) % 8 != 0:
        bits += "0" * (8 - (len(bits) % 8))
    try:
        by = bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))
        return json.loads(by.decode("utf-8", errors="strict"))
    except Exception as e:
        print("[ERROR] Zero-Width-Dekodierung fehlgeschlagen:", e)
        return None

def sha256_hex(data: str) -> str:
    """Berechnet SHA-256-Hash eines Textes."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

# ==========================================================
# Hauptfunktion: Integritätsprüfung
# ==========================================================

def integrity_check(hs_path="HS_Final.txt", backup_path="HS_Final_first.txt"):
    """
    Prüft die Integrität der HS-Datei anhand Zero-Width-Block oder sichtbarem Metablock.
    Gibt True/False zurück, abhängig vom Erfolg der Prüfung.
    """
    hs_file = Path(hs_path)
    if not hs_file.exists():
        print("❌ HS_Final.txt nicht gefunden.")
        return False

    content = read_file(hs_file)
    stripped = strip_zero_chars(content)
    actual_hash = sha256_hex(stripped)

    meta = decode_zero_block(content)
    if not meta:
        print("[WARN] Kein gültiger Zero-Width-Block erkannt – versuche Wiederherstellung aus sichtbarem Block...")
        visible_meta = decode_visible_meta(content)
        if visible_meta:
            expected_hash = visible_meta.get("sha256")
        else:
            print("[ERROR] Kein sichtbarer Block vorhanden – Wiederherstellung nicht möglich.")
            return False
    else:
        expected_hash = meta.get("sha256")

    if not expected_hash:
        print("[ERROR] Kein gültiger Hash gefunden.")
        return False

    if actual_hash != expected_hash:
        print("⚠️ Integritätsprüfung fehlgeschlagen!")
        print(f"   Erwartet: {expected_hash[:12]}... | Aktuell: {actual_hash[:12]}...")
        # Reparaturversuch
        if Path(backup_path).exists():
            print("[INFO] Wiederherstellung aus Backup...")
            shutil.copy2(backup_path, hs_file)
            print("[OK] HS_Final.txt aus Backup wiederhergestellt.")
            return True
        else:
            print("[WARN] Kein Backup gefunden – manuelle Prüfung erforderlich.")
            return False

    print("✅ Integritätsprüfung erfolgreich – Datei unverändert.")
    return True


# ==========================================================
# Wrapper für Backend-Kompatibilität (check_file)
# ==========================================================

def check_file(path: str):
    """
    Kompatibler Wrapper für app_verify_backend_v5_9.
    Führt integrity_check() aus und liefert strukturierte Ergebnisse.
    """
    result = {
        "file": path,
        "status": "unknown",
        "sha256": None,
        "verified": False,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error": None,
    }

    try:
        ok = integrity_check(hs_path=path)
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
            result["sha256"] = hashlib.sha256(data.encode("utf-8")).hexdigest()
        result["status"] = "ok" if ok else "fail"
        result["verified"] = ok
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


# ==========================================================
# Direkter Aufruf (Standalone)
# ==========================================================

if __name__ == "__main__":
    print(json.dumps(check_file("HS_Final_embedded_v3.py"), indent=4, ensure_ascii=False))
