# =============================================
# 🧠 Elaris Verify Backend – Version 4.3
# Lokale Token-Erstellung nach erfolgreicher Aktivierung
# =============================================

from flask import Flask, request, jsonify, send_file
import json, base64, os
from datetime import datetime

app = Flask(__name__)

# === Hilfsfunktionen ===

def save_token_locally(data):
    """Erstellt lokale Token-Dateien nach erfolgreicher Aktivierung"""
    os.makedirs("tokens", exist_ok=True)
    json_path = os.path.join("tokens", "verify_token.json")
    txt_path = os.path.join("tokens", "verify_token.txt")

    # JSON speichern
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Base64-Variante
    token_base64 = base64.b64encode(json.dumps(data).encode()).decode()
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(token_base64)

    return txt_path


# === Endpunkte ===

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "ok",
        "message": "Elaris Verify Backend läuft.",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route("/status", methods=["GET"])
def get_status():
    """Prüft, ob ein Token existiert und gibt Status aus"""
    token_path = os.path.join("tokens", "verify_token.json")
    if os.path.exists(token_path):
        with open(token_path, "r", encoding="utf-8") as f:
            token_data = json.load(f)
        return jsonify({
            "status": "success",
            "message": "Gespeicherter Aktivierungsstatus gefunden.",
            "data": token_data
        })
    else:
        return jsonify({
            "status": "inactive",
            "message": "Kein gespeicherter Status vorhanden."
        })


@app.route("/verify", methods=["POST"])
def verify():
    """
    Simuliert die Aktivierungsverifikation:
    - HS und KoDa werden geprüft
    - Bei Erfolg: Aktivierung & Token-Erstellung
    """
    try:
        data = request.get_json(force=True)
        hs_ok = data.get("hs_verified", False)
        koda_ok = data.get("koda_verified", False)
        integrity_ok = data.get("integrity_verified", False)

        if hs_ok and koda_ok and integrity_ok:
            # Aktivierung erfolgreich
            token_data = {
                "activated": True,
                "hs_verified": True,
                "koda_verified": True,
                "integrity_verified": True,
                "level": 1,
                "last_update": datetime.utcnow().isoformat()
            }
            token_file = save_token_locally(token_data)

            return jsonify({
                "status": "success",
                "message": "Aktivierung erfolgreich, Token erstellt.",
                "token_file": token_file,
                "token_download": "/download_token"
            })
        else:
            return jsonify({
                "status": "failed",
                "message": "Eine oder mehrere Prüfungen fehlgeschlagen."
            })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })


@app.route("/download_token", methods=["GET"])
def download_token():
    """Download-Link für den Token"""
    path = os.path.join("tokens", "verify_token.txt")
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    else:
        return jsonify({
            "status": "error",
            "message": "Kein Token vorhanden."
        })


# === Lokaler Test-Start ===
if __name__ == "__main__":
    os.makedirs("tokens", exist_ok=True)
    app.run(host="0.0.0.0", port=5000)
