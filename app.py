from flask import Flask, request, jsonify
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

STORAGE_FILE = "verify_storage.json"

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
        "expires_at": None
    }

def load_state():
    if not os.path.exists(STORAGE_FILE):
        return default_state()
    with open(STORAGE_FILE, "r", encoding="utf-8") as f:
        try:
            state = json.load(f)
            # fehlende Keys auffüllen (z. B. bei alten Versionen)
            for key, val in default_state().items():
                if key not in state:
                    state[key] = val
            return state
        except json.JSONDecodeError:
            return default_state()

def save_state(state):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def verify_signature(main_file, sig_file):
    """Prüft, ob Hash aus Signatur mit Dateiinhalt übereinstimmt"""
    try:
        content = main_file.read().decode("utf-8")
        sig_data = json.load(sig_file)
        expected_hash = sig_data.get("sha256")

        # Reset Pointer
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

# ---------------------------
# 🌐 API-Endpunkte
# ---------------------------
@app.route("/")
def index():
    return jsonify({
        "service": "Elaris Verify Backend",
        "status": "online",
        "version": "1.3",
        "info": "Backend mit zeitlich begrenzter Stufe-1-Aktivierung"
    })

@app.route("/status", methods=["GET"])
def status():
    state = check_expiry(load_state())
    return jsonify({
        "state": state,
        "message": "✅ Status abgerufen" if state["activated"] else "🔒 Kein aktiver Freigabestatus"
    })

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
    state["activated"] = True
    state["level"] = 1
    state["last_update"] = datetime.now(timezone.utc).isoformat()
    state["expires_at"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    save_state(state)

    return jsonify({
        "hs_verified": True,
        "level": 1,
        "activated": True,
        "expires_at": state["expires_at"],
        "message": "✅ HS-Datei erfolgreich geprüft – Stufe 1 aktiviert (⏳ zeitlich begrenzt)"
    }), 200

@app.route("/upload_koda", methods=["POST"])
def upload_koda():
    koda_file = request.files.get("koda")
    sig_file = request.files.get("signature")

    if not koda_file or not sig_file:
        return jsonify({"error": "KoDa-Datei oder Signatur fehlt"}), 400

    if not verify_signature(koda_file, sig_file):
        return jsonify({"error": "Integritätsprüfung fehlgeschlagen"}), 400

    state = load_state()
    state["koda_verified"] = True
    state["activated"] = True
    state["level"] = 2
    state["last_update"] = datetime.now(timezone.utc).isoformat()
    state["expires_at"] = None  # keine Zeitbegrenzung mehr
    save_state(state)

    return jsonify({
        "koda_verified": True,
        "level": 2,
        "activated": True,
        "message": "✅ KoDa-Datei erfolgreich geprüft – Stufe 2 dauerhaft aktiviert"
    }), 200

@app.route("/verify", methods=["POST"])
def verify_combined():
    try:
        data = request.get_json(silent=True) or {}
        state = load_state()

        if "hs_verified" in data:
            state["hs_verified"] = bool(data["hs_verified"])
        if "koda_verified" in data:
            state["koda_verified"] = bool(data["koda_verified"])
        if "integrity_verified" in data:
            state["integrity_verified"] = bool(data["integrity_verified"])
        if "activated" in data:
            state["activated"] = bool(data["activated"])
        if "level" in data:
            state["level"] = int(data["level"])

        # Ablaufzeit für Stufe 1 setzen
        if state["level"] == 1 and state["hs_verified"] and not state["koda_verified"]:
            state["expires_at"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        # Bei Stufe 2 unbegrenzt
        if state["level"] == 2 and state["koda_verified"]:
            state["expires_at"] = None

        state = check_expiry(state)
        state["last_update"] = datetime.now(timezone.utc).isoformat()
        save_state(state)

        return jsonify({
            "status": "ok",
            "new_state": state,
            "message": "✅ Status erfolgreich geprüft oder aktualisiert"
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/reset", methods=["POST", "GET"])
def reset_state():
    state = default_state()
    save_state(state)
    return jsonify({"message": "🔄 Zurückgesetzt", "new_state": state})

# ---------------------------
# 🚀 Start (Render)
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
