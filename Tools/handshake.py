# C:\Users\mnold_t1ohvc3\Documents\neue_KI_chatGPT_Elaris\Elairs_gatekeeper\handshake.py
# 🔐 Elaris Handshake v5 – Zero-Width Meta-Prüfung, Integritätscheck & Starter-Summe
# Erstellt: 2025-09-27
# Zweck: Verbindet HS_Final.txt + KonDa_Final.txt über Zero-Width-Metadaten,
# prüft Integrität und erzeugt handshake_report.json

import json
import re
import hashlib
from pathlib import Path
from datetime import datetime
import shutil
import os
import sys

# Prüfen, ob Skript im Reparaturmodus gestartet wurde
is_repair_mode = "--no-handshake" in sys.argv


# =========================================
# INTEGRITÄTSCHECK
# =========================================

def strip_zero_chars(text: str) -> str:
    return re.sub(r"[\u200B-\u200F\u2060\uFEFF]", "", text)

def decode_visible_meta(content: str):
    m = re.search(r"#⟐HS-META-BEGIN\s*(\{.*?\})\s*#⟐HS-META-END", content, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception as e:
        print("[ERROR] Sichtbarer Metablock fehlerhaft:", e)
        return None

def decode_zero_block_simple(content: str):
    """Vereinfachte Erkennung Zero-Width (reiner 200B/200C Block)"""
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
        print("[ERROR] Zero-Width-Block fehlerhaft:", e)
        return None

def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def integrity_check(hs_path="HS_Final.txt", backup_path="HS_Final_first.txt"):
    hs_file = Path(hs_path)
    if not hs_file.exists():
        print("❌ HS_Final.txt nicht gefunden.")
        return False

    content = hs_file.read_text(encoding="utf-8")
    stripped = strip_zero_chars(content)
    actual_hash = sha256_hex(stripped)

    meta = decode_zero_block_simple(content)
    if not meta:
        print("[WARN] Kein gültiger Zero-Width-Block erkannt – Fallback auf sichtbaren Block...")
        meta = decode_visible_meta(content)
        if not meta:
            print("[ERROR] Keine Metadaten auffindbar.")
            return False

    expected_hash = meta.get("sha256")
    if not expected_hash:
        print("[ERROR] Kein SHA256-Wert in Metadaten gefunden.")
        return False

    if actual_hash != expected_hash:
        print("⚠️ Integritätsprüfung fehlgeschlagen!")
        print(f"   Erwartet: {expected_hash[:12]}... | Aktuell: {actual_hash[:12]}...")
        if Path(backup_path).exists():
            print("[INFO] Wiederherstellung aus Backup...")
            shutil.copy2(backup_path, hs_file)
            print("[OK] HS_Final.txt aus Backup wiederhergestellt.")
            return "repaired"
        else:
            print("[WARN] Kein Backup vorhanden – manuelle Prüfung erforderlich.")
            return False

    print("✅ Integritätsprüfung erfolgreich – HS_Final.txt unverändert.")
    return "ok"


# =========================================
# HANDSHAKE-FUNKTIONEN
# =========================================

def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def decode_zero_block(content: str) -> dict:
    """Sucht und decodiert Zero-Width JSON oder sichtbare Fallback-Metadaten"""
    pattern_begin_end = r"#⟐HS-ZW-BEGIN\s*([\u200B-\u200F\u2060\s]+?)#⟐HS-ZW-END"
    match = re.search(pattern_begin_end, content, re.S)
    if not match:
        match = re.search(r"#⟐HS-ZW:\s*([\u200B-\u200F\u2060]+)", content)
    if not match:
        m2 = re.search(r"#⟐HS-META-BEGIN\s*(\{.*?\})\s*#⟐HS-META-END", content, re.S)
        if m2:
            try:
                print("[INFO] Sichtbarer Fallback-Meta-Block gefunden.")
                return json.loads(m2.group(1))
            except:
                return None
        return None
    zw_raw = match.group(1)
    zw_chars = [c for c in zw_raw if c in "\u200b\u200c"]
    bits = ''.join('0' if c == '\u200b' else '1' for c in zw_chars)
    if len(bits) % 8 != 0:
        bits += '0' * (8 - (len(bits) % 8))
    try:
        decoded_bytes = bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))
        meta = json.loads(decoded_bytes.decode("utf-8", errors="strict"))
        print("[DEBUG] JSON erfolgreich dekodiert.")
        return meta
    except Exception:
        return None

def verify_meta(path: Path):
    content = read_file(path)
    meta = decode_zero_block(content)
    if not meta:
        return None, "❌ Zero-Width-Block fehlt oder fehlerhaft"

    stripped = strip_zero_chars(content)
    calculated = sha256_hex(stripped)
    if meta.get("sha256") != calculated:
        return meta, "⚠️ SHA256 stimmt nicht überein"
    return meta, "✅ OK"


# =========================================
# HANDSHAKE
# =========================================

def handshake(hs_path: Path, koda_path: Path, out_path: Path):
    print("[AUTO] Integritätsprüfung läuft...")
    integrity_status = integrity_check(hs_path)

    # Basisreport mit Reparatur-Log
    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "initial",
        "details": {},
        "sums": {},
        "repair_log": []
    }

    # Reparaturstatus erfassen und ggf. Embed neu ausführen
    if integrity_status == "repaired":
        report["repair_log"].append({
            "event": "auto_repair_triggered",
            "source": "HS_Final.txt",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        print("[INFO] Datei wurde repariert – starte Reparaturlauf im Nur-Einbettungsmodus...")
        os.system("python embed_starter_into_hs_v3.py --no-handshake")
        print("[OK] Reparaturlauf abgeschlossen. Handshake wird jetzt beendet.")
        report["status"] = "repaired"
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return  # Beendet Handshake nach Reparatur sicher

    elif integrity_status is False:
        print("❌ Integritätsprüfung fehlgeschlagen – Handshake abgebrochen.")
        report["status"] = "failed"
        report["repair_log"].append({
            "event": "integrity_failed_no_repair",
            "source": "HS_Final.txt",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return

    # Nach erfolgreichem Check: Prüfung der Metadaten
    hs_meta, hs_status = verify_meta(hs_path)
    koda_meta, koda_status = verify_meta(koda_path)

    report["details"]["HS_Final"] = hs_status
    report["details"]["KoDa_Final"] = koda_status

    # Falls Metadaten fehlen
    if not hs_meta or not koda_meta:
        report["status"] = "failed"
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print("❌ Handshake fehlgeschlagen – Zero-Width-Metadaten fehlen.")
        return

    # Summenberechnung
    try:
        hs_sum = int(hs_meta["sha256"], 16)
        koda_sum = int(koda_meta["sha256"], 16)
        starter_sum = (hs_sum + koda_sum) % (2 ** 256)
        report["status"] = "success"
        report["sums"] = {
            "hs_sum": hs_meta["sha256"],
            "koda_sum": koda_meta["sha256"],
            "starter_sum_hex": hex(starter_sum),
        }
        print("✅ Handshake erfolgreich abgeschlossen.")
        print(f"🔢 Starter-Summe: {hex(starter_sum)}")
    except Exception as e:
        report["status"] = "error"
        report["error"] = str(e)
        print("❌ Fehler bei Summenberechnung:", e)

    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"📄 Report gespeichert in: {out_path}")


# =========================================
# MAIN
# =========================================

if __name__ == "__main__":
    base = Path.cwd()
    hs_path = base / "HS_Final.txt"
    koda_path = base / "KonDa_Final.txt"
    out_path = base / "handshake_report.json"
    handshake(hs_path, koda_path, out_path)
