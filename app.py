from flask import Flask, request, jsonify
import hashlib
import json
import os
from datetime import datetime

app = Flask(__name__)

STORAGE_FILE = "verify_storage.json"


# ---------------------------
# 📦 Hilfsfunktionen
# ---------------------------
def load_state():
    if not os.path.exists(STORAGE_FILE):
        return {"hs_verified": False, "koda_verified": False, "last_update": None}
    with open(STORAGE_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"hs_verified": False, "koda_verified": False, "last_update": None}


def save_state(state):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def verify_signature(main_file, sig_file):
    """Prüft, ob Hash aus Signatur mit Dateiinhalt übereinstimmt"""
    try:
        content = main_file.read().decode("utf-8")
        sig_data = json.load(sig_file)
        expected_hash = sig_data.get("sha256")

        # Reset Pointer, damit Datei bei Bedarf erneut gelesen werden kann
        main_file.seek(0)
        sig_file.seek(0)

        actual_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return expected_hash == actual_hash
    except Exception as e:
        print("Fehler bei verify_signature:", e)
        return False


# ---------------------------
# 🌐 API-Endpunkte
# ---------------------------

@app.route("/")
def index():
    return jsonify({
        "service": "Elaris Verify Backend",
        "status": "online",
        "version": "1.2",
        "info": "Backend zur Speicherung und Signaturprüfung der Elaris-Freigabe"
    })


@app.route("/status", methods=["GET"])
def status():
    state = load_state()
    return jsonify(state)


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
    state["last_update"] = datetime.utcnow().isoformat()
    save_state(state)

    return jsonify({
        "hs_verified": True,
        "message": "HS-Datei erfolgreich geprüft und signiert verifiziert ✅"
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
    state["last_update"] = datetime.utcnow().isoformat()
    save_state(state)

    return jsonify({
        "koda_verified": True,
        "message": "KoDa-Datei erfolgreich geprüft und signiert verifiziert ✅"
    }), 200


# ---------------------------
# ✅ Kombinierte Prüf-Route
# ---------------------------
@app.route("/verify", methods=["POST"])
def verify_combined():
    """
    Kombinierte Prüf- und Speicherroute.
    Wird von ChatGPT oder dem Client aufgerufen,
    um Status abzufragen oder zu aktualisieren.
    """
    try:
        data = request.get_json(silent=True) or {}
        state = load_state()

        # Optional: Update-Trigger falls GPT oder Frontend etwas übergibt
        if "hs_verified" in data:
            state["hs_verified"] = bool(data["hs_verified"])
        if "koda_verified" in data:
            state["koda_verified"] = bool(data["koda_verified"])

        state["last_update"] = datetime.utcnow().isoformat()
        save_state(state)

        return jsonify({
            "status": "ok",
            "hs_verified": state["hs_verified"],
            "koda_verified": state["koda_verified"],
            "last_update": state["last_update"],
            "message": "Status erfolgreich geprüft oder aktualisiert ✅"
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/reset", methods=["POST", "GET"])
def reset_state():
    state = {"hs_verified": False, "koda_verified": False, "last_update": None}
    save_state(state)
    return jsonify({
        "message": "Zurückgesetzt",
        "new_state": state
    })


# ---------------------------
# 🚀 Start (Render)
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
