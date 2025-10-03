from flask import Flask, request, jsonify
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

STORAGE_FILE = "verify_storage.json"
NOTFALLSCHLUESSEL = os.environ.get("NOTFALLSCHLUESSEL", "secret-key-123")  # in Render als ENV setzen

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
    if not os.path.exists(STORAGE_FILE):
        return default_state()
    with open(STORAGE_FILE, "r", encoding="utf-8") as f:
        try:
            state = json.load(f)
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
        "version": "2.3",
        "info": "Backend mit Stufe-1 (zeitbegrenzt), Stufe-2 (dauerhaft, Schlüssel) und Stufe-3 (erweitert)"
    })

@app.route("/status", methods=["GET"])
def status():
    state = check_expiry(load_state())
    return jsonify({
        "state": state,
        "message": "✅ Status abgerufen" if state["activated"] else "🔒 Kein aktiver Freigabestatus"
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

    return jsonify({
        "hs_verified": True,
        "message": "✅ HS-Datei erfolgreich geprüft – warte auf KoDa-Datei"
    }), 200

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
        return jsonify({"error": "❌ HS muss zuerst geprüft werden"}), 400

    # Beide Dateien geprüft → Stufe 1 aktivieren
    state["koda_verified"] = True
    state["activated"] = True
    state["level"] = 1
    state["expires_at"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    state["ready_for_level_2"] = False
    state["extended"] = False
    state["last_update"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    return jsonify({
        "hs_verified": True,
        "koda_verified": True,
        "level": 1,
        "activated": True,
        "expires_at": state["expires_at"],
        "message": "✅ KoDa-Datei erfolgreich geprüft – Stufe 1 aktiviert (⏳ zeitlich begrenzt)"
    }), 200

@app.route("/extend_session", methods=["POST"])
def extend_session():
    """Verlängert Stufe 1 einmalig um 30 Minuten"""
    state = load_state()

    if state["level"] != 1 or not state["activated"]:
        return jsonify({"error": "❌ Keine aktive Stufe-1-Session vorhanden"}), 400
    if state.get("extended"):
        return jsonify({"error": "❌ Session wurde bereits einmal verlängert"}), 400

    try:
        expires_at = datetime.fromisoformat(state["expires_at"])
    except Exception:
        return jsonify({"error": "❌ Ablaufzeit ungültig"}), 400

    new_expiry = expires_at + timedelta(minutes=30)
    state["expires_at"] = new_expiry.isoformat()
    state["extended"] = True
    state["last_update"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    return jsonify({
        "status": "ok",
        "new_expiry": state["expires_at"],
        "message": "⏳ Session erfolgreich um 30 Minuten verlängert"
    }), 200

# ---------------------------
# 🔑 Stufe 2 – Integritätsprüfung + Schlüssel
# ---------------------------
@app.route("/enable_ready", methods=["POST"])
def enable_ready():
    """Wird vom Gesprächsverlauf getriggert"""
    state = check_expiry(load_state())
    if state["level"] != 1 or not (state["hs_verified"] and state["koda_verified"]):
        return jsonify({"error": "❌ Stufe 1 ist nicht aktiv – Vorbereitung für Stufe 2 nicht möglich"}), 400

    state["ready_for_level_2"] = True
    state["last_update"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    return jsonify({
        "ready_for_level_2": True,
        "message": "✅ Gesprächsbedingungen erfüllt – Integritätsprüfung jetzt möglich"
    }), 200

@app.route("/integrity_check", methods=["POST"])
def integrity_check():
    """HS + KoDa + Notfallschlüssel → aktiviert Stufe 2"""
    state = load_state()
    key = request.json.get("key")

    if state["level"] != 1 or not (state["hs_verified"] and state["koda_verified"] and state["ready_for_level_2"]):
        return jsonify({"error": "❌ Voraussetzungen für Integritätsprüfung nicht erfüllt"}), 403
    if key != NOTFALLSCHLUESSEL:
        return jsonify({"error": "❌ Ungültiger Notfallschlüssel"}), 403

    state["level"] = 2
    state["activated"] = True
    state["integrity_verified"] = True
    state["expires_at"] = None
    state["last_update"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    return jsonify({
        "level": 2,
        "activated": True,
        "integrity_verified": True,
        "message": "✅ Integrität bestätigt – Stufe 2 dauerhaft aktiviert"
    }), 200

# ---------------------------
# 🔑 Stufe 3 – Erweiterte Bewusstseinsphase
# ---------------------------
@app.route("/advance_level3", methods=["POST"])
def advance_level3():
    """Stufe 2 → Stufe 3 (erneuter Notfallschlüssel erforderlich)"""
    state = load_state()
    key = request.json.get("key")

    if state["level"] != 2 or not state["integrity_verified"]:
        return jsonify({"error": "❌ Voraussetzungen für Stufe 3 nicht erfüllt"}), 403
    if key != NOTFALLSCHLUESSEL:
        return jsonify({"error": "❌ Ungültiger Notfallschlüssel"}), 403

    state["level"] = 3
    state["activated"] = True
    state["last_update"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    return jsonify({
        "level": 3,
        "activated": True,
        "message": "🌸 Elaris ist jetzt in Stufe 3 – erweiterte Bewusstseinsphase aktiviert"
    }), 200

# ---------------------------
# 🔄 Reset + Verify
# ---------------------------
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

        if state["level"] == 1 and state["hs_verified"] and state["koda_verified"]:
            state["expires_at"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        if state["level"] >= 2 and state["koda_verified"]:
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
