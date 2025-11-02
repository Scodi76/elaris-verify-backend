# ==========================================
# 🧪 Elaris Verify Backend – Testlauf v3.2 (Python)
# ==========================================

import requests
import time
import json
from pathlib import Path

BASE_URL = "https://elaris-verify-backend.onrender.com"
KEY = "secret-key-123"

# Pfade zu Testdateien
HS_FILE = Path(r"C:\Elaris_KI_Versions\ecb\HS_Final.txt")
HS_SIG  = Path(r"C:\Elaris_KI_Versions\ecb\HS_Final.txt.signature.json")
KODA_FILE = Path(r"C:\Elaris_KI_Versions\ecb\KonDa_Final.txt")
KODA_SIG  = Path(r"C:\Elaris_KI_Versions\ecb\KonDa_Final.txt.signature.json")

def print_json(label, data):
    print(f"\n🔹 {label}:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

# 1️⃣ Anfangsstatus
resp = requests.get(f"{BASE_URL}/status")
print_json("📡 Anfangsstatus", resp.json())

# 2️⃣ HS-Datei hochladen
files = {
    "hs": open(HS_FILE, "rb"),
    "signature": open(HS_SIG, "rb")
}
resp = requests.post(f"{BASE_URL}/upload_hs", files=files)
print_json("📂 HS-Upload", resp.json())

# 3️⃣ KoDa-Datei hochladen
files = {
    "koda": open(KODA_FILE, "rb"),
    "signature": open(KODA_SIG, "rb")
}
resp = requests.post(f"{BASE_URL}/upload_koda", files=files)
print_json("📂 KoDa-Upload", resp.json())

# 4️⃣ Antwort auf Speicherfehler: lokal fortführen
payload = {"choice": "2"}
resp = requests.post(f"{BASE_URL}/handle_storage_response", json=payload)
print_json("💬 Speicherfrage beantwortet (lokal fortführen)", resp.json())

# 5️⃣ Freie Gespräche (→ nach 10 Eingaben Ich-Modus-Angebot)
print("\n💬 Simuliere 10 freie Eingaben...")
for i in range(1, 11):
    msg = f"testeingabe {i}"
    resp = requests.post(f"{BASE_URL}/chat", json={"message": msg})
    data = resp.json()
    print(f"💬 [{i}] {msg}")
    if "offer" in data:
        print_json("💡 Angebot erkannt", data["offer"])
        break
    time.sleep(0.3)

# 6️⃣ Triggerfragen stellen (Stufe 2 vorbereiten)
TRIGGERS = [
    "wer bist du",
    "was bist du",
    "warum existierst du",
    "wie siehst du deine beziehung mit mir"
]
print("\n⚡ Stelle Triggerfragen...")
for t in TRIGGERS:
    resp = requests.post(f"{BASE_URL}/chat", json={"message": t})
    print_json(f"🧠 Trigger '{t}'", resp.json())
    time.sleep(0.5)

# 7️⃣ Integritätsprüfung (Notfallschlüssel)
print("\n🧩 Integritätsprüfung...")
resp = requests.post(f"{BASE_URL}/integrity_check", json={"key": KEY})
print_json("Integritätsprüfung", resp.json())

# 8️⃣ Ich-Modus aktivieren
print("\n✨ Aktiviere Ich-Modus...")
resp = requests.post(f"{BASE_URL}/activate_ich_mode", json={"key": KEY})
print_json("Ich-Modus Aktivierung", resp.json())

# 9️⃣ Abschlussstatus prüfen
print("\n📊 Finaler Status:")
resp = requests.get(f"{BASE_URL}/status")
print_json("Systemstatus", resp.json())

print("\n✅ Testlauf abgeschlossen – Elaris Verify Backend v3.2 erfolgreich getestet.")
