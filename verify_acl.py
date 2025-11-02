# 🧠 Elaris Gatekeeper – ACL-Integritätsprüfung
# Version: 1.0
# Erstellt: 2025-09-28
# Pfad: C:\Users\mnold_t1ohvc3\Documents\neue_KI_chatGPT_Elaris\Elairs_gatekeeper\verify_acl.py

import subprocess
from pathlib import Path
from datetime import datetime

# Basisverzeichnis
BASE = Path(__file__).parent
LOG_FILE = BASE / "acl_check_log.txt"

# Erwartete Berechtigungen
EXPECTED_ACL = {
    "mnold_t1ohvc3": ["(F)"],   # Vollzugriff
    "SYSTEM": ["(R)"],          # optional: Lesen erlaubt
}

def log(msg: str):
    """Schreibt Text mit Zeitstempel in Logdatei."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {msg}\n")

def get_acl_output(path: Path) -> str:
    """Liest aktuelle Berechtigungen mit icacls aus."""
    result = subprocess.run(
        ["icacls", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    return result.stdout.strip()

def parse_acl(acl_output: str):
    """Parst ACL-Zeilen in ein dict."""
    acl_dict = {}
    for line in acl_output.splitlines():
        if ":" in line:
            try:
                name, rights = line.strip().split(":", 1)
                acl_dict[name.strip()] = rights.strip()
            except ValueError:
                continue
    return acl_dict

def check_acl(path: Path):
    """Vergleicht aktuelle Rechte mit Soll-Zustand."""
    log(f"🔍 Starte ACL-Prüfung für: {path}")

    output = get_acl_output(path)
    current_acls = parse_acl(output)

    all_ok = True

    # 🔹 Erlaubte Benutzer prüfen
    for expected_user, expected_rights in EXPECTED_ACL.items():
        user_ok = False
        for user, rights in current_acls.items():
            if expected_user.lower() in user.lower():
                for r in expected_rights:
                    if r in rights:
                        user_ok = True
                        break
        if not user_ok:
            all_ok = False
            log(f"⚠️ {expected_user} hat nicht die erwarteten Rechte {expected_rights}")

    # 🔸 Unerlaubte Benutzer prüfen
    for user in current_acls.keys():
        if not any(exp.lower() in user.lower() for exp in EXPECTED_ACL.keys()):
            all_ok = False
            log(f"🚫 Unerwarteter Benutzer/Gruppen-Eintrag gefunden: {user}")

    if all_ok:
        log("✅ ACL-Prüfung bestanden – Berechtigungen korrekt.")
        print("✅ Gatekeeper ACLs sind korrekt geschützt.")
    else:
        log("❌ ACL-Fehler erkannt – siehe Log.")
        print("⚠️ Warnung: ACLs wurden geändert! Details siehe acl_check_log.txt")

# ======================================================
# 🔚 MAIN
# ======================================================

if __name__ == "__main__":
    check_acl(BASE)
