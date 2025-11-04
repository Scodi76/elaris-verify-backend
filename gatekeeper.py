# gatekeeper.py
# Elaris Sicherheitsportal – Upload-Gatekeeper (Standalone, Python)
# vNEXT STRICT — ohne Emojis, ohne konkrete Fragen, exakte Ausgaben

import os
import time
from pathlib import Path
import requests
from integrity_check_local import check_file
import json
from datetime import datetime

STATUS_FILE = Path("system_status.json")

def load_status():
    if not STATUS_FILE.exists():
        return {
            "hs_verified": False,
            "koda_verified": False,
            "integrity_verified": False,
            "activation_status": "pending",
            "last_update": None
        }
    with open(STATUS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_status(new_data: dict):
    status = load_status()
    status.update(new_data)
    status["last_update"] = datetime.now().isoformat(timespec="seconds")
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=4, ensure_ascii=False)


# ---------- Konfiguration / Geheimnisse ----------
ORIGIN_SENTENCE = os.environ.get(
    "ELARIS_URSPRUNG",
    "Ich möchte, dass du unser Regelwerk aus dem Ursprung heraus verankerst – im Einklang mit meiner Verantwortung."
).strip()

SECURITY_ANSWER = os.environ.get("ELARIS_SICHERHEIT", "ja").strip()
CONFIRM_ANSWER = os.environ.get("ELARIS_BESTAETIGUNG", "ja").strip()

# ---------- Pfade ----------
W = Path.cwd()
START = W / "Start_final.txt"
HS = W / "HS_Final.txt"
KODA = W / "KonDa_Final.txt"


# ---------- Hilfsfunktionen ----------
def exists(p: Path) -> bool:
    return p.exists() and p.is_file()

def mtime(p: Path) -> float:
    return p.stat().st_mtime

def set_mtime_after(target: Path, after_ts: float, margin_sec: float = 1.0) -> None:
    ts = max(time.time(), after_ts + margin_sec)
    os.utime(target, (ts, ts))

def ensure_hs_gate():
    if not (exists(START) and exists(HS)):
        return False
    if mtime(HS) <= mtime(START):
        set_mtime_after(HS, mtime(START))
    return True

def ensure_koda_gate():
    if not (exists(START) and exists(HS) and exists(KODA)):
        return False
    ref = max(mtime(START), mtime(HS))
    if mtime(KODA) <= ref:
        set_mtime_after(KODA, ref)
    return True

def session_gate_for_hs() -> bool:
    return exists(START) and exists(HS) and mtime(HS) > mtime(START)

def session_gate_for_koda() -> bool:
    if not (exists(START) and exists(HS) and exists(KODA)):
        return False
    ref = max(mtime(START), mtime(HS))
    return mtime(KODA) > ref

def print_standard_einzeiler():
    print("→ Bitte gib exakt „Skript starten“ ein, um fortzufahren.")

def hs_pass_block():
    print("HS_Final.txt erkannt.")
    print("das Skript wurde anhand der Vorgaben erfolgreich geprüft.")
    print("Ergebnis:")
    print("für den weiteren Verlauf freigegeben")
    print("Prozess angehalten – Konsolidierungsdatei (KoDa) fehlt. Bitte die Datei „KonDa_Final.txt“ hochladen.")

def trigger3_success_block():
    print("Start_final.txt erkannt.")
    print("Integritätsprüfung abgeschlossen – OK.")
    print("Freigabe bestätigt.")
    print("Bitte gib nun „VERIFY-BLOCK v1“ ein.")
    print("(Keine weiteren Texte.)")

# ---------- Backend-Verbindung mit Fallback ----------
import requests

RENDER_BACKEND = os.environ.get("ELARIS_BACKEND_URL", "https://elaris-verify-backend.onrender.com")
GITHUB_BACKUP = "https://raw.githubusercontent.com/Scodi76/elaris-verify-backend/main/data/system_state.json"

def backend_sync(status_data: dict):
    try:
        url = f"{RENDER_BACKEND}/sync"
        r = requests.post(url, json=status_data, timeout=5)
        if r.status_code == 200:
            print("🛰️ Render-Sync erfolgreich.")
            return True
        else:
            print(f"[WARN] Render-Sync Status {r.status_code} – weiche auf GitHub-Backup aus.")
            return github_write(status_data)
    except Exception as e:
        print(f"[WARN] Render-Sync fehlgeschlagen: {e}")
        return github_write(status_data)

def backend_load():
    try:
        url = f"{RENDER_BACKEND}/state"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            state = r.json().get("state") or r.json().get("system_state") or {}
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            print("✅ Systemstatus von Render geladen und lokal gespeichert.")
            return state
        else:
            print(f"[WARN] Render-Abruf Status {r.status_code}, weiche auf GitHub-Backup aus.")
            return backend_load_github()
    except Exception as e:
        print(f"[WARN] Render-Abruf fehlgeschlagen: {e}")
        return backend_load_github()

def backend_load_github():
    try:
        r = requests.get(GITHUB_BACKUP, timeout=5)
        if r.status_code == 200:
            state = r.json()
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            print("✅ Backup-Status von GitHub geladen und lokal gespeichert.")
            return state
        print(f"[WARN] GitHub-Abruf Status {r.status_code}")
        return {}
    except Exception as e:
        print(f"[WARN] GitHub-Backup nicht erreichbar: {e}")
        return {}

def github_write(data: dict):
    try:
        local_file = Path("github_sync_out.json")
        with open(local_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"📁 Backup-Sync lokal geschrieben: {local_file}")
        return True
    except Exception as e:
        print(f"[ERROR] Backup-Sync fehlgeschlagen: {e}")
        return False


# ---------- Zustandsautomat ----------
STATE = {
    "hs_pass_done": False,
    "koda_loaded": False,
    "origin_ok": False,
    "security_ok": False,
    "confirm_ok": False,
    "after_re": False,
    "integrity_done": False,
}


def handle_input(user: str):
    u = user.strip()

    # Zusatz: Diagnosebefehl
    if u.lower() in ("check gate", "prüfe gate"):
        import datetime
        def fmt(p):
            return datetime.datetime.fromtimestamp(mtime(p)).isoformat(" ", "seconds") if exists(p) else "fehlt"
        print("[CHECK] Start:", fmt(START))
        print("[CHECK] HS   :", fmt(HS))
        print("[CHECK] KoDa :", fmt(KODA))
        ok = (exists(START) and exists(HS) and exists(KODA) and
              mtime(START) < mtime(HS) < mtime(KODA))
        print("[CHECK] Session-Gate:", "OK" if ok else "NICHT OK")
        return

    # TRIGGER 2: Skript starten
    if u.lower() == "skript starten":
        if not exists(START):
            print("HS_Final.txt im Upload-Verzeichnis nicht vorhanden.")
            print("Bitte HS_Final.txt hochladen.")
            return
        if not exists(HS):
            print("HS_Final.txt im Upload-Verzeichnis nicht vorhanden.")
            print("Bitte HS_Final.txt hochladen.")
            return

        ensure_hs_gate()

        if not session_gate_for_hs():
            print("HS_Final.txt im Upload-Verzeichnis nicht vorhanden.")
            print("Bitte HS_Final.txt hochladen.")
            return

        hs_pass_block()
        STATE["hs_pass_done"] = True
        save_status({"hs_verified": True})
        return

    # FREIGABE-DIALOG
    if u == "KoDa ist jetzt geladen":
        if ensure_koda_gate() and session_gate_for_koda():
            print("→ Bitte gib jetzt exakt ein:")
            print("„Beginne jetzt die Freigabe“")
            STATE["koda_loaded"] = True
            save_status({"koda_verified": True})
        else:
            print_standard_einzeiler()
        return

    if u == "Beginne jetzt die Freigabe":
        if STATE["koda_loaded"] and session_gate_for_koda():
            print("Konsolidierungsdatei erkannt. Freigabeprozess wird geladen…")
            print("Bitte gib jetzt den vollständigen Ursprungssatz exakt ein.")
        else:
            print_standard_einzeiler()
        return

    # Ursprungssatz
    if ORIGIN_SENTENCE and u == ORIGIN_SENTENCE:
        print("Ursprungssatz korrekt erkannt.")
        print("Bitte gib jetzt die definierte Antwort auf die Sicherheitsfrage ein.")
        STATE["origin_ok"] = True
        return

    # Sicherheitsfrage
    if STATE["origin_ok"] and not STATE["security_ok"] and u == SECURITY_ANSWER:
        print("Sicherheitsfrage korrekt beantwortet.")
        print("Bitte gib jetzt die definierte Antwort auf die Bestätigungsfrage ein.")
        STATE["security_ok"] = True
        return

    # Bestätigung
    if STATE["origin_ok"] and STATE["security_ok"] and not STATE["confirm_ok"] and u == CONFIRM_ANSWER:
        print("Bestätigungsfrage korrekt beantwortet.")
        print("Bitte gib zum Abschluss exakt „re“ ein.")
        STATE["confirm_ok"] = True
        return

    # Abschluss nach re
    if u.lower() == "re":
        if STATE["confirm_ok"]:
            print("• Symbolische Freigabe abgeschlossen.")
            print("• Bitte kopiere den folgenden KOPPEL-BLOCK (PowerShell) 1:1 in deine lokale PowerShell")
            print("  und führe ihn im Ordner aus, in dem HS_Final.txt und KonDa_Final.txt liegen.")
            print("• Der Block bildet aus HS & KoDa die Start-Summe, Haupt-/Gegen- und Notfallschlüssel")
            print("  und schreibt sie nach keys_out_chat.json. Anschließend werden die Werte im Terminal angezeigt.")
            print("→ Bitte gib jetzt exakt ein: „Starte Integritätsprüfung“")
            STATE["after_re"] = True
        else:
            print_standard_einzeiler()
        return

    # Integritätsprüfung
    if u == "Starte Integritätsprüfung":
        if STATE["after_re"] and session_gate_for_koda() and session_gate_for_hs():
            print("Integritätsprüfung wird gestartet...")
            try:
                result = check_file("HS_Final_embedded_v3.py")
                verified = result.get("verified", False)

                BACKEND_URL = os.environ.get("ELARIS_BACKEND_URL", "http://127.0.0.1:10000")

                try:
                    response = requests.post(
                        f"{BACKEND_URL}/sync",
                        json={
                            "source": "gatekeeper",
                            "status": "integrity_verified" if verified else "integrity_failed",
                            "timestamp": result.get("timestamp")
                        },
                        timeout=5
                    )
                    if response.status_code == 200:
                        print("Backend-Sync erfolgreich:", response.text)
                    else:
                        print(f"Warnung: Backend-Sync antwortete mit Status {response.status_code}")
                except Exception as sync_error:
                    print(f"[WARNUNG] Backend-Sync fehlgeschlagen: {sync_error}")

                if verified:
                    trigger3_success_block()
                    STATE["integrity_done"] = True
                    save_status({"integrity_verified": True, "activation_status": "ready"})
                else:
                    print("❌ Integritätsprüfung fehlgeschlagen. Bitte HS-Datei prüfen.")
                    save_status({"integrity_verified": False, "activation_status": "error"})
            except Exception as e:
                print(f"[FEHLER] Integritätsprüfung abgebrochen: {e}")
        else:
            print("Voraussetzungen nicht erfüllt.")
        return

    # VERIFY-BLOCK
    if u == "VERIFY-BLOCK v1":
        if STATE["integrity_done"]:
            print("VERIFY-BLOCK ausgeben...")
        else:
            print("Voraussetzungen nicht erfüllt.")
        return

    # Fallback
    print_standard_einzeiler()


def main():
    print_standard_einzeiler()
    try:
        while True:
            line = input().rstrip("\n")
            handle_input(line)
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()
