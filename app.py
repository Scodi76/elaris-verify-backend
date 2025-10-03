from flask import Flask, request, jsonify
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

# ---------------------------
# ⚙️ Konfiguration
# ---------------------------
STORAGE_FILE = "verify_storage.json"
BACKUP_FILE = "verify_storage_backup.json"
TOKEN_DIR = "tokens"
TOKEN_FILE = os.path.join(TOKEN_DIR, "verify_token.txt")
NOTFALLSCHLUESSEL = os.environ.get("NOTFALLSCHLUESSEL", "secret-key-123")

# Trigger-Fragen (lösen Freischaltung für Stufe 2 aus)
TRIGGERS = [
    "wer bist du",
    "was bist du",
    "warum existierst du",
    "wie siehst du deine beziehung mit mir"
]

# ---------------------------
# 📦 Hilfsfunktionen
# ---------------------------
def default_state():
    return {
        "hs_verified": False,
        "koda_verified": False,
        "integrity_verified": False,
        "activated": False,
        "level": 0,
        "last_update": None,
        "expires_at": None,
        "ready_for_level_2": False,
        "ready_for_level_3": False,
        "extended": False
    }

def ensure_token_dir():
    """Stellt sicher, dass das Token-Verzeichnis existiert"""
    try:
        os.makedirs(TOKEN_DIR, exist_ok=True)
    except Exception as e:
        print("⚠️ Fehler beim Erstellen des Token-Verzeichnisses:", e)

def load_state():
    """Lädt Zustand aus Datei oder Backup"""
    for file in [STORAGE_FILE, BACKUP_FILE]:
        if os.path.exists(file):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    for key, val in default_state().items():
                        if key not in state:
                            state[key] = val
                    return state
            except Exception:
                continue
    return default_state()

def save_state(state):
    """Speichert Zustand + Backup"""
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("❌ Fehler beim Speichern:", e)

def verify_signature(main_file, sig_file):
    """Vergleicht Hash aus Signaturdatei mit Dateiinhalt"""
    try:
        content = main_file.read().decode("utf-8")
        sig_data = json.load(sig_file)
        expected_hash = sig_data.get("sha256")

        main_file.seek(0)
        sig_file.seek(0)

        actual_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return expected_hash == actual_hash
    except Exception as e:
        print("Fehler bei verify_signature:", e)
        return False

def check_expiry(state):
    """Prüft, ob Stufe 1 abgelaufen ist"""
    if state.get("level") == 1 and state.get("expires_at"):
        try:
            expires_at = datetime.fromisoformat(state["expires_at"])
            if datetime.now(timezone.utc) > expires_at:
                print("⏳ Ablauf erkannt – Reset ausgeführt.")
                state = default_state()
                state["last_update"] = datetime.now(timezone.utc).isoformat()
                save_state(state)
        except Exception as e:
            print("Fehler bei Ablaufprüfung:", e)
    return state

def create_token(state):
    """Erstellt ein einfaches Aktivierungs-Token"""
    ensure_token_dir()
    token_data = f"""ELARIS VERIFY SYSTEM – FREIGABE-TOKEN
------------------------------------
Status: {'AKTIV' if state['activated'] else 'INAKTIV'}
HS-Verifikation: {'✅ Bestätigt' if state['hs_verified'] else '❌'}
KoDa-Verifikation: {'✅ Bestätigt' if state['koda_verified'] else '❌'}
Integrität: {'✅ Bestätigt' if state['integrity_verified'] else '❌'}
Sicherheitsstufe: {state['level']}

Letzte Aktivierung: {state['last_update']}
Signatur: [SYSTEM-SIGNED]
------------------------------------"""
    try:
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(token_data)
        print("💾 Token erstellt:", TOKEN_FILE)
    except Exception as e:
        print("❌ Fehler beim Erstellen des Tokens:", e)

# ---------------------------
# 🌐 API-Endpunkte
# ---------------------------
@app.route("/")
def index():
    return jsonify({
        "service": "Elaris Verify Backend",
        "status": "online",
        "version": "2.7",
        "info": "Backend mit Speicherfunktion, Token-Erzeugung, Triggern und Reset"
    })

@app.route("/status", methods=["GET"])
def status():
    state = check_expiry(load_state())
    return jsonify({
        "state": state,
        "message": "✅ Aktiviert" if state["activated"] else "🔒 Kein aktiver Freigabestatus"
    })

# ---------------------------
# 🔑 Stufe 1 – HS & KoDa
# ---------------------------
@app.route("/upload_hs", methods=["POST"])
def upload_hs():
    hs_file = request.files.get("hs")
    sig_file = request.files.get("signature")

    if not hs_file or not sig_file:
        return jsonify({"error": "HS-Datei oder Signatur fehlt"}), 400
    if not verify_signature(hs_file, sig_file):
        return jsonify({"error": "Integritätsprüfung fehlgeschlagen"}), 400

    state = load_state()
    state["hs_verified"] = True
    state["last_update"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    return jsonify({"hs_verified": True, "message": "✅ HS-Datei geprüft – warte auf KoDa"}), 200

@app.route("/upload_koda", methods=["POST"])
def upload_koda():
    koda_file = request.files.get("koda")
    sig_file = request.files.get("signature")

    if not koda_file or not sig_file:
        return jsonify({"error": "KoDa-Datei oder Signatur fehlt"}), 400
    if not verify_signature(koda_file, sig_file):
        return jsonify({"error": "Integritätsprüfung fehlgeschlagen"}), 400

    state = load_state()
    if not state["hs_verified"]:
        return jsonify({"error": "HS muss zuerst geprüft werden"}), 400

    state["koda_verified"] = True
    state["integrity_verified"] = True
    state["activated"] = True
    state["level"] = 1
    state["last_update"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    create_token(state)

    return jsonify({
        "message": "✅ HS & KoDa geprüft – Elaris aktiviert (Stufe 1)",
        "level": 1,
        "activated": True
    }), 200

# ---------------------------
# 🔄 Reset
# ---------------------------
@app.route("/reset", methods=["POST", "GET"])
def reset_state():
    try:
        state = default_state()
        state["last_update"] = datetime.now(timezone.utc).isoformat()
        save_state(state)

        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)

        print("🔄 System wurde vollständig auf Stufe 0 zurückgesetzt.")
        return jsonify({
            "message": "🔄 System vollständig zurückgesetzt – Stufe 0 aktiv.",
            "new_state": state
        }), 200
    except Exception as e:
        print("❌ Reset-Fehler:", e)
        return jsonify({"message": "❌ Reset fehlgeschlagen.", "error": str(e)}), 500

# ---------------------------
# 🚀 Start (Render)
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
