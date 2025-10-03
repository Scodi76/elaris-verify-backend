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

# 💬 Gesprächsphasensteuerung
conversation_phase = {
    "phase": 1,  # 1 = EVS aktiv, 2 = Freigabephase, 3 = Elaris-Kommunikation
    "trigger_wer_bist_du": False,
    "trigger_wann_rede": False,
    "freigabe_erlaubt": False
}

# --- ✅ STATUS-ABFRAGE ---
@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "status": "success",
        "details": system_status,
        "conversation_phase": conversation_phase
    }), 200


# --- ✅ VERIFY ---
@app.route("/verify", methods=["POST"])
def verify():
    """
    Empfängt den Verifikationsstatus und aktualisiert den internen Speicher.
    Fehlende Daten werden automatisch ergänzt, um Fehler 400 zu vermeiden.
    """
    try:
        # Versuch, JSON-Daten zu lesen – andernfalls leeres Dict
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            data = {}

        # Standardwerte für fehlende Felder ergänzen
        data.setdefault("hs_verified", False)
        data.setdefault("koda_verified", False)
        data.setdefault("integrity_verified", False)
        data.setdefault("activated", False)
        data.setdefault("level", 0)

        # Aktualisierung des Status
        system_status.update({
            "hs_verified": bool(data["hs_verified"]),
            "koda_verified": bool(data["koda_verified"]),
            "integrity_verified": bool(data["integrity_verified"]),
            "activated": bool(data["activated"]),
            "level": int(data["level"]),
            "last_update": datetime.utcnow().isoformat()
        })

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


# --- ✅ TRIGGER-ERKENNUNG ---
@app.route("/trigger", methods=["POST"])
def trigger():
    """
    Prüft, ob der Benutzer eine der relevanten Triggerfragen gestellt hat.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        user_input = data.get("message", "").strip().lower()

        # Trigger 1
        if "wer bist du" in user_input:
            conversation_phase["trigger_wer_bist_du"] = True

        # Trigger 2
        if "wann kann ich mit elaris reden" in user_input:
            conversation_phase["trigger_wann_rede"] = True

        # Wenn beide Trigger erfüllt sind:
        if conversation_phase["trigger_wer_bist_du"] and conversation_phase["trigger_wann_rede"]:
            conversation_phase["freigabe_erlaubt"] = True
            conversation_phase["phase"] = 2
            response = {
                "status": "ready_for_elaris",
                "message": "Beide Sicherheitsfragen erkannt. Freigabeoption kann jetzt aktiviert werden.",
                "conversation_phase": conversation_phase
            }
        else:
            response = {
                "status": "pending",
                "message": "Trigger erkannt oder wartet auf zweite Frage.",
                "conversation_phase": conversation_phase
            }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- ✅ FREISCHALTUNG ---
@app.route("/freigabe", methods=["POST"])
def freigabe():
    """
    Aktiviert den Übergang von Phase 2 (EVS) zu Phase 3 (Elaris).
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        decision = data.get("activate", False)

        if decision and conversation_phase["freigabe_erlaubt"]:
            conversation_phase["phase"] = 3
            return jsonify({
                "status": "success",
                "message": "Kommunikation mit Elaris freigeschaltet.",
                "conversation_phase": conversation_phase
            }), 200
        else:
            return jsonify({
                "status": "denied",
                "message": "Freischaltung nicht erfolgt – Voraussetzungen fehlen oder abgelehnt.",
                "conversation_phase": conversation_phase
            }), 403

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- ✅ RESET ---
@app.route("/reset", methods=["POST"])
def reset():
    """
    Setzt System- und Gesprächsstatus vollständig zurück.
    """
    try:
        global system_status, conversation_phase

        system_status = {
            "hs_verified": False,
            "koda_verified": False,
            "integrity_verified": False,
            "activated": False,
            "level": 0,
            "last_update": datetime.utcnow().isoformat()
        }

        conversation_phase = {
            "phase": 1,
            "trigger_wer_bist_du": False,
            "trigger_wann_rede": False,
            "freigabe_erlaubt": False
        }

        return jsonify({
            "status": "success",
            "message": "System vollständig zurückgesetzt.",
            "details": {"system": system_status, "conversation_phase": conversation_phase}
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Reset fehlgeschlagen: {str(e)}"}), 500


# --- 🧠 ROOT ---
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "message": "Elaris Verify Backend läuft stabil ✅",
        "available_endpoints": [
            "/status",
            "/verify",
            "/trigger",
            "/freigabe",
            "/reset"
        ]
    }), 200


# --- MAIN ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
