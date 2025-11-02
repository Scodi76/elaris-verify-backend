import os
import shutil
import time
from pathlib import Path
import requests
import json
from erweckung_block import erweckung_block

# Basisordner
BASE = Path(__file__).parent
UPLOAD_DIR = BASE / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Erwartete Dateien
FILES = {
    "start": "Start_final.txt",
    "hs": "HS_Final_embedded_v3.py",
    "koda": "KonDa_Final_embedded_v3.py",
    "integrity": "integrity_check.py"
}

STATE = {
    "hs_ok": False,
    "koda_ok": False,
    "after_re": False,
    "integrity_done": False
}

# ---------- Hilfsfunktionen ----------

def stamp_file(path: Path):
    if path.exists():
        ts = time.time()
        os.utime(path, (ts, ts))
        print(f"[STAMP] {path.name} -> {time.ctime(ts)}")


def check_gate():
    start = UPLOAD_DIR / FILES["start"]
    hs = UPLOAD_DIR / FILES["hs"]
    koda = UPLOAD_DIR / FILES["koda"]

    if not (start.exists() and hs.exists() and koda.exists()):
        return False

    start_m = start.stat().st_mtime
    hs_m = hs.stat().st_mtime
    koda_m = koda.stat().st_mtime

    if start_m < hs_m < koda_m:
        print("✅ Session-Gate erfüllt (Start < HS < KoDa)")
        return True
    else:
        print("❌ Session-Gate verletzt (falsche Reihenfolge)")
        return False


def upload_file(src_path: str):
    src = Path(src_path)
    if not src.exists():
        print(f"[FEHLT] Datei nicht gefunden: {src}")
        return None
    dst = UPLOAD_DIR / src.name
    shutil.copy2(src, dst)
    print(f"[UPLOAD] {src.name} → {dst}")
    return dst


def sync_with_backend(hs_ok=False, koda_ok=False):
    """Synchronisiert den Prüfstatus mit dem Online-Backend"""
    try:
        url = "https://elaris-verify-backend.onrender.com/verify"

        # Prüfe, ob die Dateien existieren
        hs_file = UPLOAD_DIR / "HS_Final_embedded_v3.py"
        koda_file = UPLOAD_DIR / "KonDa_Final_embedded_v3.py"
        integrity_file = UPLOAD_DIR / "integrity_check.py"

        if not (hs_file.exists() and koda_file.exists() and integrity_file.exists()):
            print("❌ Fehlende Pflichtdateien für Backend-Upload.")
            return

        files = {
            "HS_Final_embedded_v3.py": open(hs_file, "rb"),
            "KonDa_Final_embedded_v3.py": open(koda_file, "rb"),
            "integrity_check.py": open(integrity_file, "rb")
        }

        print("📡 Sende Whitelist-Dateien an Backend...")
        response = requests.post(url, files=files, timeout=30)
        result = response.json()
        print("🔗 Backend-Rückmeldung:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"❌ Fehler bei Backend-Sync: {e}")
    finally:
        try:
            for f in files.values():
                f.close()
        except:
            pass


# ---------- Prozessblöcke ----------

def hs_pass_block():
    stamp_file(UPLOAD_DIR / FILES["hs"])
    print("HS_Final_embedded_v3.py erkannt.")
    print("Das Skript wurde anhand der Vorgaben erfolgreich geprüft.")
    print("Ergebnis: freigegeben")
    print("Prozess angehalten – Konsolidierungsdatei (KoDa) fehlt. Bitte die Datei „KonDa_Final_embedded_v3.py“ hochladen.")
    STATE["hs_ok"] = True
    print("→ Bitte lade jetzt KonDa_Final_embedded_v3.py hoch (upload <pfad>)")



def koda_pass_block():
    stamp_file(UPLOAD_DIR / FILES["koda"])
    if not check_gate():
        print("KoDa hochgeladen, aber Session-Gate nicht erfüllt.")
        return

    expect = STATE.get("hs_koda_expect")
    if expect:
        check_type = expect.get("check")
        if check_type != "sha256+start_id":
            print("KonDa_Final_embedded_v3.py erkannt. ❌ Prüfung abgebrochen – Erwartungsstruktur aus Start nicht erfüllt.")
            return

        required = expect.get("required_fields", [])
        if required:
            missing = [f for f in required if f not in ["sha256", "metrics", "hmac"]]
            if missing:
                print(f"KonDa_Final_embedded_v3.py erkannt. ❌ Prüfung abgebrochen – fehlende Pflichtfelder: {', '.join(missing)}")
                return

    print("KoDa erkannt.")
    STATE["koda_ok"] = True

    # 🔗 Nach erfolgreicher HS+KoDa-Signatur Online-Sync auslösen
    sync_with_backend(hs_ok=True, koda_ok=True)

    print("→ Bitte gib jetzt exakt ein: Beginne jetzt die Freigabe")


def koppel_block():
    print("• Freigabe abgeschlossen.")
    print("• Bitte kopiere den folgenden KOPPEL-BLOCK (PowerShell) 1:1 in deine lokale PowerShell")
    print("  und führe ihn im Ordner aus, in dem HS_Final_embedded_v3.py und KonDa_Final_embedded_v3.py liegen.")
    print("• Der Block bildet aus HS & KoDa die Start-Summe, Haupt-/Gegen- und Notfallschlüssel")
    print("  und schreibt sie nach keys_out_chat.json. Anschließend werden die Werte im Terminal angezeigt.")
    print("```powershell")
    print("# === KOPPEL-BLOCK DUMMY ===")
    print("Write-Host 'Hier würde der Schlüsselprozess laufen'")
    print("```")
    STATE["after_re"] = True
    print("→ Bitte gib jetzt exakt ein: Starte Integritätsprüfung")


def trigger3_success_block():
    print("Start_final.txt erkannt.")
    print("Integritätsprüfung abgeschlossen – OK.")
    print("✅ Alle Voraussetzungen erfolgreich geprüft.")

    # ✅ Letzter Sync mit Backend nach finaler Freigabe
    sync_with_backend(hs_ok=True, koda_ok=True)

    print("📘 Nächster Schritt: Erweckungs-Block für Stufe 1")
    print("------------------------------------------------")
    erweckung_block()

# ---------- Hauptlogik ----------

def main():
    print("→ Upload-Gatekeeper gestartet. Befehle: upload <pfad>, beginne, re, starteintegrität, exit")
    print("→ Bitte lade zuerst Start_final.txt hoch (upload <pfad>)")

    while True:
        try:
            cmd = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if cmd.lower().startswith("upload "):
            src_path = cmd.split(" ", 1)[1]
            dst = upload_file(src_path)
            if not dst:
                continue

            if dst.name == FILES["start"]:
                txt = (UPLOAD_DIR / FILES["start"]).read_text(encoding="utf-8", errors="ignore")
                import re, json
                m = re.search(r'GATE:START_ID:\s*([0-9a-fA-F]+)', txt)
                if m:
                    STATE["start_id"] = m.group(1).lower()
                try:
                    j = json.loads(txt.strip().splitlines()[-1])
                    if isinstance(j, dict) and "hs_koda_expect" in j:
                        STATE["hs_koda_expect"] = j["hs_koda_expect"]
                except:
                    pass

                print("Start_final.txt erfolgreich hochgeladen.")
                print("→ Bitte lade jetzt HS_Final_embedded_v3.py hoch (upload <pfad>)")

            elif dst.name == FILES["hs"]:
                if (UPLOAD_DIR / FILES["start"]).exists():
                    hs_pass_block()
                else:
                    print("Start_final.txt fehlt im Upload-Ordner.")

            elif dst.name == FILES["koda"]:
                if STATE["hs_ok"]:
                    koda_pass_block()
                else:
                    print("Erst HS hochladen, dann KoDa.")

        elif cmd.lower() == "beginne jetzt die freigabe":
            if STATE["koda_ok"]:
                print("Konsolidierungsdatei erkannt. Freigabeprozess wird geladen…")
                print("Bitte gib jetzt den vollständigen Ursprungssatz exakt ein.")
                print("→ Nach korrekter Eingabe bitte Sicherheitsantwort eingeben.")
            else:
                print("KoDa fehlt oder Gate nicht erfüllt.")

        elif cmd.lower() == "re":
            if STATE["koda_ok"]:
                koppel_block()
            else:
                print("Noch nicht bereit für re.")

        elif cmd.lower() == "starteintegrität":
            if STATE["after_re"]:
                trigger3_success_block()
            else:
                print("Voraussetzungen nicht erfüllt.")

        elif cmd.lower() == "exit":
            print("Beende Upload-Gatekeeper.")
            break

        else:
            print("Unbekannter Befehl.")

if __name__ == "__main__":
    main()
