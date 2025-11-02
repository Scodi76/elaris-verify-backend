# ======================================================
# 🧠 signature_guard.py – Signaturprüfung vor Systemstart
# Version: v1.0 (Sicherheitsstufe 5+)
# Pfad: C:\Users\mnold_t1ohvc3\Documents\neue_KI_chatGPT_Elaris\Elairs_gatekeeper\signature_guard.py
# ======================================================

import json, hashlib
from pathlib import Path
from datetime import datetime

# ======================================================
# 🔍 Hauptfunktion: verify_signatures_before_start()
# ======================================================

def verify_signatures_before_start(base_path: Path, log_callback=None) -> bool:
    """
    Prüft die wichtigsten Dateien (HS_Final.txt, KonDa_Final.txt, Start_final.txt)
    gegen die gespeicherte integrity_baseline.json.
    Gibt True zurück, wenn alle Signaturen gültig sind.
    Gibt False zurück, wenn Manipulationen, fehlende Dateien oder Baseline-Fehler auftreten.
    """

    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    baseline_file = base_path / "integrity_baseline.json"
    critical_files = ["HS_Final.txt", "KonDa_Final.txt", "Start_final.txt", "HS_Final.txt.signature.json", "KonDa_Final.txt.signature.json"]

    log("\n🧠 Signaturprüfung gestartet...")

    # --------------------------------------------------
    # 1️⃣ Prüfen, ob die Baseline vorhanden ist
    # --------------------------------------------------
    if not baseline_file.exists():
        log("❌ Keine integrity_baseline.json gefunden – Prüfung abgebrochen.")
        return False

    # --------------------------------------------------
    # 2️⃣ Baseline laden
    # --------------------------------------------------
    try:
        data = json.loads(baseline_file.read_text(encoding="utf-8"))
        known_hashes = data.get("files", {})
    except Exception as e:
        log(f"[ERROR] Baseline konnte nicht gelesen werden: {e}")
        return False

    all_valid = True
    report = {"timestamp": datetime.utcnow().isoformat() + "Z", "results": {}}

    # --------------------------------------------------
    # 3️⃣ Alle kritischen Dateien prüfen
    # --------------------------------------------------
    for name in critical_files:
        file_path = base_path / name
        if not file_path.exists():
            log(f"⚠️ {name} fehlt – Start blockiert.")
            report["results"][name] = "missing"
            all_valid = False
            continue

        current_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        baseline_hash = known_hashes.get(name)

        if not baseline_hash:
            log(f"⚠️ Kein Baseline-Eintrag für {name} – Start blockiert.")
            report["results"][name] = "not_in_baseline"
            all_valid = False
            continue

        if current_hash != baseline_hash:
            log(f"❌ Manipulation erkannt bei {name}!")
            log(f"   Erwartet: {baseline_hash[:12]}..., Gefunden: {current_hash[:12]}...")
            report["results"][name] = "tampered"
            all_valid = False

            # 📘 AuditTrail-Eintrag bei Manipulation
            audit_log = base_path / "audit_trail.json"
            entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "event": "file_tampered",
                "file": name,
                "expected_hash": baseline_hash,
                "found_hash": current_hash
            }
            try:
                if audit_log.exists():
                    audit_data = json.loads(audit_log.read_text(encoding="utf-8"))
                    audit_data.append(entry)
                else:
                    audit_data = [entry]
                audit_log.write_text(json.dumps(audit_data, indent=2, ensure_ascii=False), encoding="utf-8")
                log(f"🧾 AuditTrail-Eintrag erstellt für {name}")
            except Exception as e:
                log(f"[WARN] AuditTrail konnte nicht geschrieben werden: {e}")

        else:
            log(f"✅ {name} ist signiert und unverändert.")
            report["results"][name] = "ok"

    # --------------------------------------------------
    # 4️⃣ Ergebnis speichern
    # --------------------------------------------------
    report_path = base_path / "verify_report.json"
    try:
        report["summary"] = {
            "fail": sum(1 for v in report["results"].values() if v != "ok"),
            "ok": sum(1 for v in report["results"].values() if v == "ok")
        }
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"📄 Signatur-Report aktualisiert: {report_path.name}")
    except Exception as e:
        log(f"[WARN] Konnte verify_report.json nicht schreiben: {e}")

    # --------------------------------------------------
    # 5️⃣ Rückgabe
    # --------------------------------------------------
    if not all_valid:
        log("❌ Signaturprüfung fehlgeschlagen.")
        return False

    log("🟢 Alle Signaturen sind gültig.")
    return True


# ======================================================
# 🔧 Einzeltest (optional, nur direkt ausführbar)
# ======================================================
if __name__ == "__main__":
    base = Path(__file__).parent
    result = verify_signatures_before_start(base)
    print("\nErgebnis:", "OK" if result else "BLOCKIERT")
