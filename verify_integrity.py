# 🔍 verify_integrity.py
# Prüft Integrität der Kern-Dateien inkl. Signaturverifikation (.sig)
# Version: v2.1 – erweitert um HS/KonDa-Signaturprüfung

import json, hashlib
from pathlib import Path
from datetime import datetime

# ------------------------------------------------------------
# 🧠 Utility-Funktionen
# ------------------------------------------------------------

def safe_print(*args):
    """Ersetzt Emojis durch Konsolenmarker für Powershell-Kompatibilität."""
    text = " ".join(str(a) for a in args)
    for k, v in {"🔍": "[CHECK]", "✅": "[OK]", "❌": "[ERR]", "⚠️": "[WARN]", "🧠": "[STATUS]"}.items():
        text = text.replace(k, v)
    print(text)

def sha256_hex(data): 
    """Berechnet SHA256-Hash aus Byte-Daten."""
    return hashlib.sha256(data).hexdigest()

def verify_signature(file_path: Path, sig_path: Path):
    """Vergleicht Datei-Hash mit gespeicherter Signaturdatei (.sig)."""
    try:
        if not sig_path.exists():
            return {"status": "warn", "msg": "Signatur fehlt"}

        sig = json.loads(sig_path.read_text(encoding="utf-8"))
        expected_hash = sig.get("hash")

        if not expected_hash:
            return {"status": "warn", "msg": "Ungültige Signaturdatei"}

        current_hash = sha256_hex(file_path.read_bytes())
        if current_hash == expected_hash:
            return {"status": "ok", "msg": "Signatur gültig"}
        else:
            return {"status": "fail", "msg": "Signatur ungültig"}
    except Exception as e:
        return {"status": "fail", "msg": f"Fehler: {e}"}

# ------------------------------------------------------------
# 🔍 Hauptlogik
# ------------------------------------------------------------

def main():
    base = Path(__file__).parent
    baseline = base / "integrity_baseline.json"
    report = base / "verify_report.json"

    if not baseline.exists():
        safe_print("[ERR] Keine Baseline gefunden.")
        return

    # Baseline laden
    bl = json.loads(baseline.read_text(encoding="utf-8"))
    ref = bl.get("files", {})

    results = []
    ok, warn, fail = 0, 0, 0

    # Liste aller Hauptdateien
    main_files = ["HS_Final.txt", "KonDa_Final.txt", "Start_final.txt"]

    for f in main_files:
        path = base / f
        if not path.exists():
            results.append({"file": f, "status": "fail", "msg": "Fehlt"})
            fail += 1
            continue

        data = path.read_bytes()
        current = sha256_hex(data)
        expected = ref.get(f)

        # 🔸 Vergleich mit Baseline
        if not expected:
            results.append({"file": f, "status": "warn", "msg": "Kein Referenzwert"})
            warn += 1
        elif current == expected:
            results.append({"file": f, "status": "ok", "msg": "OK"})
            ok += 1
        else:
            results.append({"file": f, "status": "fail", "msg": "Abweichung"})
            fail += 1

        # 🔹 Zusätzliche Signaturprüfung (falls vorhanden)
        sig_file = base / f.replace(".txt", ".sig")
        if sig_file.exists():
            sig_result = verify_signature(path, sig_file)
            results.append({
                "file": sig_file.name,
                "status": sig_result["status"],
                "msg": sig_result["msg"]
            })
            if sig_result["status"] == "ok":
                ok += 1
            elif sig_result["status"] == "warn":
                warn += 1
            else:
                fail += 1
        else:
            results.append({"file": sig_file.name, "status": "warn", "msg": "Signatur fehlt"})
            warn += 1

    # --------------------------------------------------------
    # Zusammenfassung
    # --------------------------------------------------------

    summary = {"ok": ok, "warn": warn, "fail": fail}
    status = "✅ OK" if fail == 0 else "❌ Fehler"

    out = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": status,
        "details": results,
        "summary": summary
    }

    report.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    safe_print("🔍 Integritätsprüfung abgeschlossen.")
    safe_print("🧠 Status:", status)
    safe_print("📘 Bericht gespeichert unter:", report.name)

if __name__ == "__main__":
    main()
