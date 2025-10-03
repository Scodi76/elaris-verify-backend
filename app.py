from flask import Flask, request, jsonify, send_file
import hashlib
import json
import os
import base64
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

# ---------------------------
# ⚙️ Konfiguration
# ---------------------------
STORAGE_FILE = "verify_storage.json"
BACKUP_FILE = "verify_storage_backup.json"
TOKEN_FILE_JSON = "verify_token.json"
TOKEN_FILE_TXT = "verify_token.txt"
NOTFALLSCHLUESSEL = os.environ.get("NOTFALLSCHLUESSEL", "secret-key-123")

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

def load_state():
    if os.path.exists(TOKEN_FILE_JSON):
        try:
            with open(TOKEN_FILE_JSON, "r", encoding="utf-8") as f:
                token_state = json.load(f)
                print("🔄 Zustand aus Token wiederhergestellt.")
                return token_state
        except Exception as e:
            print("⚠️ Token konnte nicht geladen werden:", e)

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
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("❌ Fehler beim Speichern:", e)

def create_token(state):
    """Erzeugt einen Download-Token nach erfolgreicher Aktivierung"""
    try:
        token_data = json.dumps(state, ensure_ascii=False, indent=2)
        token_b64 = base64.b64encode(token_data.encode("utf-8")).decode("utf-8")

        with open(TOKEN_FILE_JSON, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        with open(TOKEN_FILE_TXT, "w", encoding="utf-8") as f:
            f.write(token_b64)

        print("💾 Token-Dateien erstellt.")
        return True
    except Exception as e:
        print("⚠️ Token-Erstellung fehlgeschlagen:", e)
        return False

def verify_signature(main_file, sig_file):
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

# ---------------------------
# 🌐 API
# ---------------------------
@app.route("/")
def index():
    return jsonify({
        "service": "Elaris Verify Backend",
        "version": "4.2",
        "status": "online",
        "info": "HS/KoDa-Prüfung mit Token-Download"
    })

@app.route("/status", methods=["GET"])
def status():
    state = check_expiry(load_state())
    return jsonify({
        "state": state,
        "message": "✅ Aktiviert" if state["activated"] else "🔒 Kein aktiver Status erkannt"
    })

# ---------------------------
# 🔑 HS & KoDa Upload
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
    return jsonify({"hs_verified": True, "message": "✅ HS-Datei geprüft"}), 200

@app.route("/upload_koda", methods=["POST"])
def upload_koda():
    koda_file = request.files.get("koda")
    sig_file = request.files.get("signature")

    if not koda_file or not sig_file:
        return jsonify({"error": "KoDa-Datei oder Signatur fehlt"}), 400
    if not verify_signature(koda_file, sig_file):
        return jsonify({"error": "Integritätsprüfung fehlgeschlagen"}), 400

    state = check_expiry(load_state())
    if not state["hs_verified"]:
        return jsonify({"error": "HS muss zuerst geprüft werden"}), 400

    state["koda_verified"] = True
    state["activated"] = True
    state["level"] = 1
    state["expires_at"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    state["last_update"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    # 🔐 Token erstellen
    token_ok = create_token(state)

    response = {
        "hs_verified": True,
        "koda_verified": True,
        "level": 1,
        "activated": True,
        "message": "✅ HS + KoDa geprüft – Stufe 1 aktiviert"
    }

    if token_ok:
        response["download"] = "/download_token"
        response["note"] = "💾 Token wurde erzeugt. Du kannst ihn über /download_token herunterladen."

    return jsonify(response), 200

# ---------------------------
# 💾 Token-Download
# ---------------------------
@app.route("/download_token", methods=["GET"])
def download_token():
    if os.path.exists(TOKEN_FILE_TXT):
        return send_file(TOKEN_FILE_TXT, as_attachment=True)
    else:
        return jsonify({"error": "❌ Kein Token gefunden"}), 404

# ---------------------------
# 🔄 Reset
# ---------------------------
@app.route("/reset", methods=["POST", "GET"])
def reset_state():
    state = default_state()
    save_state(state)
    for f in [TOKEN_FILE_JSON, TOKEN_FILE_TXT]:
        if os.path.exists(f):
            os.remove(f)
    return jsonify({"message": "🔄 Reset ausgeführt"}), 200

# ---------------------------
# 🚀 Start
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
