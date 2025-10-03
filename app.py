from flask import Flask, request, jsonify
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
TOKEN_FILE = "verify_token.json"
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
        "extended": False
    }

def load_state():
    """Lädt Zustand oder Token"""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                token_data = json.load(f)
                encoded = token_data.get("token")
                if encoded:
                    decoded = base64.b64decode(encoded.encode()).decode()
                    state = json.loads(decoded)
                    return state
        except Exception:
            pass
    for file in [STORAGE_FILE, BACKUP_FILE]:
        if os.path.exists(file):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue
    return default_state()

def save_state(state):
    """Speichert Zustand und Token"""
    try:
        encoded = base64.b64encode(json.dumps(state).encode()).decode()
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump({"token": encoded}, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("❌ Fehler beim Speichern:", e)

def verify_signature(main_file, sig_file):
    try:
        content = main_file.read().decode("utf-8")
        sig_data = json.load(sig_file)
        expected_hash = sig_data.get("sha256")
        main_file.seek(0)
        sig_file.seek(0)
        actual_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return expected_hash == actual_hash
    except Exception:
        return False

def check_expiry(state):
    if state.get("level") == 1 and state.get("expires_at"):
        try:
            expires_at = datetime.fromisoformat(state["expires_at"])
            if datetime.now(timezone.utc) > expires_at:
                print("⏳ Ablauf erkannt – Reset ausgeführt.")
                return default_state()
        except Exception:
            pass
    return state

# ---------------------------
# 🌐 API
# ---------------------------
@app.route("/")
def index():
    return jsonify({
        "service": "Elaris Verify Backend",
        "version": "3.9",
        "info": "Mit Token-Archivierung und Status-Wiederherstellung"
    })

@app.route("/status", methods=["GET"])
def status():
    state = check_expiry(load_state())
    return jsonify({
        "state": state,
        "message": "✅ Aktiviert" if state["activated"] else "🔒 Kein aktiver Freigabestatus"
    })

# ---------------------------
# 🔑 Upload & Prüfung
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
    return jsonify({"message": "✅ HS geprüft – warte auf KoDa"}), 200

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
        return jsonify({"error": "❌ HS zuerst prüfen"}), 400

    state["koda_verified"] = True
    state["activated"] = True
    state["level"] = 1
    state["integrity_verified"] = True
    state["expires_at"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    save_state(state)

    return jsonify({
        "message": "✅ HS & KoDa geprüft – Stufe 1 aktiviert (temporär)"
    }), 200

# ---------------------------
# 💾 Archivierung & Token
# ---------------------------
@app.route("/archive", methods=["POST"])
def archive_state():
    """Archiviert aktuellen Zustand in Token"""
    state = load_state()
    if not state["activated"]:
        return jsonify({"error": "❌ Kein aktiver Zustand vorhanden"}), 400
    save_state(state)
    encoded = base64.b64encode(json.dumps(state).encode()).decode()
    return jsonify({
        "message": "💾 Zustand archiviert",
        "token": encoded
    }), 200

@app.route("/restore", methods=["POST"])
def restore_state():
    """Wiederherstellung per Token"""
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    if not token:
        return jsonify({"error": "❌ Kein Token übermittelt"}), 400
    try:
        decoded = base64.b64decode(token.encode()).decode()
        state = json.loads(decoded)
        save_state(state)
        return jsonify({
            "message": "📂 Archivierter Zustand erfolgreich wiederhergestellt",
            "state": state
        }), 200
    except Exception as e:
        return jsonify({"error": f"Token ungültig: {str(e)}"}), 400

# ---------------------------
# 🔄 Reset
# ---------------------------
@app.route("/reset", methods=["POST"])
def reset_state():
    state = default_state()
    save_state(state)
    return jsonify({"message": "🔄 System zurückgesetzt"}), 200

# ---------------------------
# 🚀 Start
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
