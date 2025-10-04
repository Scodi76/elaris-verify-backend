# 🔐 Elaris Integrity Check v1.0
# Erstellt: 2025-09-27
# Zweck: Überprüft HS_Final.txt auf Manipulation und repariert ggf. Zero-Width-Block

import json
import re
import hashlib
from pathlib import Path
import shutil

def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def strip_zero_chars(text: str) -> str:
    """Entfernt unsichtbare Steuerzeichen (Zero-Width, NBSP etc.)"""
    return re.sub(r"[\u200B-\u200F\u2060\uFEFF]", "", text)

def decode_visible_meta(content: str):
    """Liest sichtbaren Fallback-Metablock"""
    m = re.search(r"#⟐HS-META-BEGIN\s*(\{.*?\})\s*#⟐HS-META-END", content, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception as e:
        print("[ERROR] Sichtbarer Metablock fehlerhaft:", e)
        return None

def decode_zero_block(content: str):
    """Liest Zero-Width-Block"""
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
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def integrity_check(hs_path="HS_Final.txt", backup_path="HS_Final_first.txt"):
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


if __name__ == "__main__":
    integrity_check()
