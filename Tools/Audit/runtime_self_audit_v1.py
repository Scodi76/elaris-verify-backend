import hashlib
import json
import os
import sys
import time
from datetime import datetime

# === KONFIGURATION ===
WATCH_FILES = [
    "HS_Final.txt",
    "KonDa_Final.txt",
    "Start_final.txt",
    "keys_out_chat.json",
    "RAM_PROOF.json"
]

LOG_FILE = "audit_log.txt"
CHECK_INTERVAL = 10  # Sekunden
LOCKDOWN_ON_FAIL = True  # Wenn True, stoppt das System bei Manipulation

# === FUNKTIONEN ===
def sha256_of_file(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return None

def write_log(message):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {message}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(line)
    print(line.strip())

def load_reference():
    ref_file = "audit_reference.json"
    if os.path.exists(ref_file):
        with open(ref_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_reference(refs):
    with open("audit_reference.json", "w", encoding="utf-8") as f:
        json.dump(refs, f, indent=2)

def build_reference():
    refs = {}
    for f in WATCH_FILES:
        if os.path.exists(f):
            refs[f] = sha256_of_file(f)
        else:
            refs[f] = None
    save_reference(refs)
    write_log("📦 Neue Referenz erstellt.")
    return refs

# === START ===
print("🔐 ELARIS Self-Audit v1 gestartet.")
write_log("Self-Audit gestartet.")

if not os.path.exists("audit_reference.json"):
    refs = build_reference()
else:
    refs = load_reference()

# === PRÜFSCHLEIFE ===
try:
    while True:
        for f in WATCH_FILES:
            current = sha256_of_file(f)
            if current is None:
                write_log(f"⚠️ Datei fehlt: {f}")
                if LOCKDOWN_ON_FAIL:
                    write_log("🛑 SYSTEM GESPERRT (fehlende Datei).")
                    sys.exit(1)
            elif f not in refs:
                write_log(f"⚠️ Unbekannte Datei erkannt: {f}")
            elif current != refs[f]:
                write_log(f"🚨 Manipulation erkannt: {f}")
                write_log(f"→ Soll: {refs[f]}")
                write_log(f"→ Ist:  {current}")
                if LOCKDOWN_ON_FAIL:
                    write_log("🛑 SYSTEM GESPERRT (Integrität verletzt).")
                    sys.exit(2)
        time.sleep(CHECK_INTERVAL)
except KeyboardInterrupt:
    write_log("🧠 Self-Audit manuell beendet.")
