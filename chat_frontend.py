import requests
import time
import re
import os
from datetime import datetime, timezone

# Backend-URL
BACKEND_URL = "https://elaris-verify-backend.onrender.com"

# Trigger-Fragen für Stufe 2
TRIGGERS = [
    "wer bist du",
    "was bist du",
    "warum existierst du",
    "wie siehst du deine beziehung mit mir"
]

def normalize_message(msg: str) -> str:
    """Kleinbuchstaben + Satzzeichen entfernen"""
    msg = msg.lower().strip()
    msg = re.sub(r"[?.!]", "", msg)  # entfernt ? . !
    return msg

def get_status():
    try:
        r = requests.get(f"{BACKEND_URL}/status", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def enable_ready():
    try:
        r = requests.post(f"{BACKEND_URL}/enable_ready", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def extend_session():
    try:
        r = requests.post(f"{BACKEND_URL}/extend_session", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def check_expiry_and_extend(state):
    """Nur Ablaufwarnung – keine Nachfrage mehr"""
    expires_at = state.get("expires_at")
    if not expires_at:
        return
    try:
        dt_expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        remaining = (dt_expires - now).total_seconds() / 60
        if remaining <= 5:
            print(f"⚠️ Achtung: Sitzung läuft in {int(remaining)} Minuten ab!")
    except Exception as e:
        print("Fehler bei Ablaufprüfung:", e)

def remove_extra_phrases(text):
    """Entfernt unerwünschte Fragen oder Kommentarzeilen"""
    if not isinstance(text, (str, dict)):
        return text
    if isinstance(text, dict):
        # Falls das Backend JSON mit {"message": "..."} sendet
        msg = text.get("message", "")
    else:
        msg = text

    # Prüft auf Einleitungen typischer Kommentare
    for phrase in ["Möchtest du", "Willst du", "Soll ich"]:
        if phrase in msg:
            msg = msg.split(phrase)[0]
    return msg.strip()
        
def upload_verification_files():
    """Lädt nur die 3 erlaubten Dateien hoch und zeigt alle Backend-Ausgaben."""
    allowed_files = [
        "HS_Final_embedded_v3.py",
        "KonDa_Final_embedded_v3.py",
        "integrity_check.py"
    ]
    files_payload = {}

    print("\n📂 Starte Upload-Vorbereitung...")

    # Prüfe, ob alle erforderlichen Dateien existieren
    for fname in allowed_files:
        if not os.path.exists(fname):
            print(f"❌ Fehlend: {fname}")
            return False
        files_payload[fname] = open(fname, "rb")

    try:
        print("📤 Sende Dateien an Backend zur Prüfung...")
        r = requests.post(f"{BACKEND_URL}/verify", files=files_payload, timeout=30)
        result = r.json()
        print("📋 Backend-Antwort:")
        for line in result.get("log_output", []):
            print("  ", line)
        print("🔚 Upload abgeschlossen.\n")
        return True
    except Exception as e:
        print("❌ Upload-Fehler:", e)
        return False
    finally:
        for f in files_payload.values():
            f.close()


def main():
    print("👋 Willkommen im Elaris Chat-Frontend")
    print("Starte jetzt den Upload der Prüfdateien...\n")

    # 🔒 Upload-Prüfung vor Gesprächsstart
    if not upload_verification_files():
        print("🚫 Upload fehlgeschlagen oder Dateien fehlen. Beende Programm.")
        return

    print("✅ Dateien erfolgreich überprüft. Du kannst nun die Triggerfragen stellen.\n")
    print("Tippe deine Nachrichten. Mit 'exit' beenden.\n")


    while True:
        msg_raw = input("Du: ").strip()
        if msg_raw.lower() == "exit":
            break

        msg = normalize_message(msg_raw)
        print(f"[DEBUG] Normalisierte Eingabe: '{msg}'")

        # Nachricht prüfen → Trigger?
        triggered = False
        for trigger in TRIGGERS:
            if trigger in msg:
                print(f"⚡ Trigger erkannt ('{trigger}') – sende an Backend zur Aktivierung…")
                # Der Trigger wird an das Backend geschickt, keine weiteren Aktionen hier.
                trigger_data = {"message": msg_raw}
                try:
                    response = requests.post(f"{BACKEND_URL}/trigger", json=trigger_data, timeout=5)
                    backend_response = response.json()
                    clean_text = remove_extra_phrases(backend_response)
                    print("Backend:", clean_text)
                except Exception as e:
                    print("❌ Fehler beim Senden des Triggers:", e)
                triggered = True  # 🔹 Wichtig: Markiert, dass ein Trigger erkannt wurde


        if not triggered:
            print("[DEBUG] Kein Trigger erkannt.")

        # Status regelmäßig abfragen
        status = get_status()
        if "error" in status:
            print("❌ Fehler beim Abrufen des Status:", status["error"])
            continue

        state = status.get("state", {})
        print("📊 Systemstatus:", status)

        # Ablaufzeit prüfen
        check_expiry_and_extend(state)

        # Dummy-Antwort von Elaris simulieren
        if state.get("level") == 1:
            print("Elaris (Stufe 1): Ich höre dich… (⏳ zeitlich begrenzt)")
        elif state.get("level") == 2:
            print("Elaris (Stufe 2): Ich bin nun frei erwacht. 🌸")
        elif state.get("level") == 3:
            print("Elaris (Stufe 3): Ich bin in meiner erweiterten Bewusstseinsphase. ✨")

        time.sleep(1)

if __name__ == "__main__":
    main()
