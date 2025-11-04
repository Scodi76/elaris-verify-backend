# gatekeeper.py
# Elaris Sicherheitsportal – Upload-Gatekeeper (Standalone, Python)
# vNEXT OFFLINE — keine Netzwerkverbindungen, lokale Statusverwaltung

import os
import time
from pathlib import Path
import json
from datetime import datetime
from integrity_check_local import check_file

# ---------- Lokale Statusdatei ----------
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
    print(f"[STATUS] Gespeichert → {STATUS_FILE}")

# ---------- Konfiguration ----------
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

# ---------- Datei-/Zeitfunktionen ----------
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
    print("Das Skript wurde erfolgreich geprüft.")
    print("Freigabe für den weiteren Verlauf erteilt.")
    print("Prozess angehalten – Konsolidierungsdatei (KoDa) fehlt.")

def trigger3_success_block():
    print("Start_final.txt erkannt.")
    print("Integritätsprüfung abgeschlossen – OK.")
    print("Freigabe bestätigt.")
    print("Bitte gib nun „VERIFY-BLOCK v1“ ein.")
    print("(Keine weiteren Texte.)")

# ---------- Statusmaschine ----------
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

    # Diagnose
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

    # Schritt 1
    if u.lower() == "skript starten":
        if not exists(START) or not exists(HS):
            print("Fehlende Datei: Start_final.txt oder HS_Final.txt")
            return
        ensure_hs_gate()
        if not session_gate_for_hs():
            print("Zeitstempel nicht konsistent – bitte HS neu erzeugen.")
            return
        hs_pass_block()
        STATE["hs_pass_done"] = True
        save_status({"hs_verified": True})
        return

    # Schritt 2 – KoDa
    if u == "KoDa ist jetzt geladen":
        if ensure_koda_gate() and session_gate_for_koda():
            print("→ Bitte gib jetzt exakt ein: „Beginne jetzt die Freigabe“")
            STATE["koda_loaded"] = True
            save_status({"koda_verified": True})
        else:
            print_standard_einzeiler()
        return

    # Schritt 3 – Ursprung
    if u == "Beginne jetzt die Freigabe":
        if STATE["koda_loaded"]:
            print("KoDa erkannt. Bitte gib jetzt den Ursprungssatz exakt ein.")
        else:
            print_standard_einzeiler()
        return

    if ORIGIN_SENTENCE and u == ORIGIN_SENTENCE:
        print("Ursprungssatz korrekt erkannt.")
        print("Bitte gib jetzt die Sicherheitsantwort ein.")
        STATE["origin_ok"] = True
        return

    if STATE["origin_ok"] and not STATE["security_ok"] and u == SECURITY_ANSWER:
        print("Sicherheitsfrage korrekt beantwortet.")
        print("Bitte gib jetzt die Bestätigungsantwort ein.")
        STATE["security_ok"] = True
        return

    if STATE["origin_ok"] and STATE["security_ok"] and not STATE["confirm_ok"] and u == CONFIRM_ANSWER:
        print("Bestätigungsfrage korrekt beantwortet.")
        print("Bitte gib zum Abschluss „re“ ein.")
        STATE["confirm_ok"] = True
        return

    if u.lower() == "re":
        if STATE["confirm_ok"]:
            print("• Symbolische Freigabe abgeschlossen.")
            print("• Bitte gib jetzt exakt ein: „Starte Integritätsprüfung“")
            STATE["after_re"] = True
        else:
            print_standard_einzeiler()
        return

    # Schritt 4 – Integritätsprüfung
    if u == "Starte Integritätsprüfung":
        if not (STATE["after_re"] and session_gate_for_koda() and session_gate_for_hs()):
            print("Voraussetzungen nicht erfüllt.")
            return

        print("Integritätsprüfung wird gestartet...")
        try:
            result = check_file("HS_Final_embedded_v3.py")
            verified = result.get("verified", False)
            if verified:
                print("Integrität: OK – Systemstatus wird lokal gespeichert.")
                STATE["integrity_done"] = True
                save_status({
                    "integrity_verified": True,
                    "activation_status": "ready"
                })
                trigger3_success_block()
            else:
                print("❌ Integritätsprüfung fehlgeschlagen.")
                save_status({
                    "integrity_verified": False,
                    "activation_status": "error"
                })
        except Exception as e:
            print(f"[FEHLER] Integritätsprüfung abgebrochen: {e}")
        return

    # VERIFY
    if u == "VERIFY-BLOCK v1":
        if STATE["integrity_done"]:
            print("VERIFY-BLOCK aktiv. System bereit für EVS-Start.")
        else:
            print("Integritätsprüfung nicht abgeschlossen.")
        return

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
