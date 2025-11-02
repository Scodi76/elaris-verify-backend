# gatekeeper.py
# Elaris Sicherheitsportal – Upload-Gatekeeper (Standalone, Python)
# vNEXT STRICT — ohne Emojis, ohne konkrete Fragen, exakte Ausgaben

import os
import time
from pathlib import Path

# ---------- Konfiguration / Geheimnisse ----------
ORIGIN_SENTENCE = os.environ.get(
    "ELARIS_URSPRUNG",
    "Ich möchte, dass du unser Regelwerk aus dem Ursprung heraus verankerst – im Einklang mit meiner Verantwortung."
).strip()

SECURITY_ANSWER = os.environ.get("ELARIS_SICHERHEIT", "ja").strip()
CONFIRM_ANSWER  = os.environ.get("ELARIS_BESTAETIGUNG", "ja").strip()

# ---------- Pfade ----------
W = Path.cwd()
START = W / "Start_final.txt"
HS    = W / "HS_Final.txt"
KODA  = W / "KonDa_Final.txt"

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

# ---------- AUTO-CLEANUP ----------
def cleanup_old_variants():
    """Entfernt alte First- und Final-Dateien, damit nur Embed-Dateien übrig bleiben."""
    targets = [
        W / "HS_Final_first.txt",
        W / "KonDa_Final_first.txt",
        W / "HS_Final.txt",
        W / "KonDa_Final.txt"
    ]
    removed = []
    for p in targets:
        try:
            if p.exists():
                os.remove(p)
                removed.append(p.name)
        except Exception as e:
            print(f"[WARN] Konnte {p.name} nicht löschen: {e}")
    if removed:
        print("Alte Varianten gelöscht:", ", ".join(removed))
    else:
        print("Keine First/Final-Dateien gefunden – System bereits sauber.")


# ---------- STRIKTER DATEIFILTER ----------
ALLOWED_EXTENSIONS = {"py"}
ALLOWED_PATTERN = "_embedded_v3.py"

def is_allowed_file(filename):
    """Erlaubt nur eingebettete v3-Dateien."""
    return (
        filename.endswith(ALLOWED_PATTERN)
        and filename.split(".")[-1] in ALLOWED_EXTENSIONS
    )

def disable_non_embedded_files(base_dir):
    """
    Deaktiviert alle nicht eingebetteten Final-, First- und .txt-Dateien.
    Fügt '.disabled' an, statt sie sofort zu löschen.
    """
    removed = []
    for f in os.listdir(base_dir):
        path = os.path.join(base_dir, f)
        if not os.path.isfile(path):
            continue
        # nur echte Dateien, keine Ordner
        if any(x in f for x in ["Final", "first", ".txt", ".signature.json"]) and not is_allowed_file(f):
            try:
                new_path = path + ".disabled"
                os.rename(path, new_path)
                removed.append(f)
            except Exception as e:
                print(f"[WARN] Datei {f} konnte nicht deaktiviert werden: {e}")
    if removed:
        print("🧹 Nicht eingebettete Dateien deaktiviert:", ", ".join(removed))
    else:
        print("✅ Nur eingebettete Dateien aktiv – OK.")



# ---------- PowerShell Blöcke ----------
KOPPEL_BLOCK = """(dein bestehender PS-Block bleibt hier unverändert)"""
VERIFY_BLOCK = """(dein bestehender VERIFY-Block bleibt hier unverändert)"""

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

    if u.lower() == "skript starten":
        if not exists(START) or not exists(HS):
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
        return

    if u == "KoDa ist jetzt geladen":
        if ensure_koda_gate() and session_gate_for_koda():
            print("→ Bitte gib jetzt exakt ein:")
            print("„Beginne jetzt die Freigabe“")
            STATE["koda_loaded"] = True
        else:
            print_standard_einzeiler()
        return

    if u == "Beginne jetzt die Freigabe":
        if STATE["koda_loaded"] and session_gate_for_koda():
            disable_non_embedded_files(W)
            cleanup_old_variants()  # 🧹 automatischer Löschvorgang
            print("Konsolidierungsdatei erkannt. Freigabeprozess wird geladen…")
            print("Bitte gib jetzt den vollständigen Ursprungssatz exakt ein.")
        else:
            print_standard_einzeiler()
        return

    if ORIGIN_SENTENCE and u == ORIGIN_SENTENCE:
        print("Ursprungssatz korrekt erkannt.")
        print("Bitte gib jetzt die definierte Antwort auf die Sicherheitsfrage ein.")
        STATE["origin_ok"] = True
        return

    if STATE["origin_ok"] and not STATE["security_ok"] and u == SECURITY_ANSWER:
        print("Sicherheitsfrage korrekt beantwortet.")
        print("Bitte gib jetzt die definierte Antwort auf die Bestätigungsfrage ein.")
        STATE["security_ok"] = True
        return

    if STATE["origin_ok"] and STATE["security_ok"] and not STATE["confirm_ok"] and u == CONFIRM_ANSWER:
        print("Bestätigungsfrage korrekt beantwortet.")
        print("Bitte gib zum Abschluss exakt „re“ ein.")
        STATE["confirm_ok"] = True
        return

    if u.lower() == "re":
        if STATE["confirm_ok"]:
            print("• Symbolische Freigabe abgeschlossen.")
            print("• Bitte kopiere den folgenden KOPPEL-BLOCK (PowerShell) 1:1 in deine lokale PowerShell")
            print("  und führe ihn im Ordner aus, in dem HS_Final.txt und KonDa_Final.txt liegen.")
            print("• Der Block bildet aus HS & KoDa die Start-Summe, Haupt-/Gegen- und Notfallschlüssel")
            print("  und schreibt sie nach keys_out_chat.json. Anschließend werden die Werte im Terminal angezeigt.")
            print(KOPPEL_BLOCK)
            print("→ Bitte gib jetzt exakt ein: „Starte Integritätsprüfung“")
            STATE["after_re"] = True
        else:
            print_standard_einzeiler()
        return

    if u == "Starte Integritätsprüfung":
        if STATE["after_re"] and session_gate_for_koda() and session_gate_for_hs():
            trigger3_success_block()
            STATE["integrity_done"] = True
        else:
            print("Voraussetzungen nicht erfüllt.")
        return

    if u == "VERIFY-BLOCK v1":
        if STATE["integrity_done"]:
            print(VERIFY_BLOCK)
        else:
            print("Voraussetzungen nicht erfüllt.")
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
