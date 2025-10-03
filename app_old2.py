from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# 🧩 Statusspeicher
system_status = {
    "hs_verified": False,
    "koda_verified": False,
    "integrity_verified": False,
    "activated": False,
    "level": 0,
    "last_update": None
}

# --- ✅ STATUS-ABFRAGE ---
@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "status": "success",
        "details": system_status
    }), 200


# --- ✅ VERIFY ---
@app.route("/verify", methods=["POST"])
def verify():
    """
    Empfängt den Verifikationsstatus und aktualisiert den internen Speicher.
    Stellt sicher, dass IMMER eine JSON-Antwort zurückkommt.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        if not data:
            return jsonify({
                "status": "error",
                "message": "Keine oder ungültige JSON-Daten empfangen."
            }), 400

        # Aktualisierung des Status
        system_status.update({
            "hs_verified": data.get("hs_verified", False),
            "koda_verified": data.get("koda_verified", False),
            "integrity_verified": data.get("integrity_verified", False),
            "activated": data.get("activated", False),
            "level": data.get("level", 0),
            "last_update": datetime.utcnow().isoformat()
        })

        # Erfolgreiche Bestätigung zurückgeben
        return jsonify({
            "status": "success",
            "message": "Verifikationsdaten empfangen und erfolgreich gespeichert.",
            "received_data": data,
            "current_status": system_status
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Unerwarteter Fehler: {str(e)}"
        }), 500


# --- ✅ RESET ---
@app.route("/reset", methods=["POST"])
def reset():
    """
    Setzt den gesamten Freigabestatus vollständig zurück.
    """
    try:
        global system_status
        system_status = {
            "hs_verified": False,
            "koda_verified": False,
            "integrity_verified": False,
            "activated": False,
            "level": 0,
            "last_update": datetime.utcnow().isoformat()
        }

        return jsonify({
            "status": "success",
            "message": "System wurde vollständig zurückgesetzt.",
            "details": system_status
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Reset fehlgeschlagen: {str(e)}"
        }), 500


# --- 🧠 ROOT ---
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "message": "Elaris Verify Backend läuft stabil ✅",
        "available_endpoints": ["/status", "/verify", "/reset"]
    }), 200


# --- MAIN ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
