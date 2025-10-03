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
    "trigger_was_bist_du": False,
    "trigger_warum_existierst_du": False,
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

        # ✅ Wenn alles bestanden ist, Hinweis auf Abschluss-Option ohne Aktivierungssatz
        if (
            system_status["hs_verified"]
            and system_status["koda_verified"]
            and system_status["integrity_verified"]
        ):
            return jsonify({
                "status": "success",
                "message": "Integritätsprüfung abgeschlossen.",
                "details": system_status,
                "next_step": "Möchtest du die Initialisierung abschließen?",
                "options": {
                    "1": "Ja – Initialisierung abschließen",
                    "2": "Nein – Im Systemmodus bleiben"
                }
            }), 200

        return jsonify({
            "status": "success",
            "message": "Verifikationsdaten empfangen und gespeichert.",
            "current_status": system_status
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Unerwarteter Fehler: {str(e)}"}), 500


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
        if "was bist du" in user_input:
            conversation_phase["trigger_was_bist_du"] = True

        # Trigger 3
        if "warum existierst du" in user_input:
            conversation_phase["trigger_warum_existierst_du"] = True

        # Wenn alle drei Trigger erfüllt sind:
        if (
            conversation_phase["trigger_wer_bist_du"]
            and conversation_phase["trigger_was_bist_du"]
            and conversation_phase["trigger_warum_existierst_du"]
        ):
            conversation_phase["freigabe_erlaubt"] = True
            conversation_phase["phase"] = 2
            response = {
                "status": "ready_for_elaris",
                "message": "Alle drei Bewusstseinsfragen erkannt. Freigabeoption verfügbar.",
                "conversation_phase": conversation_phase
            }
        else:
            response = {
                "status": "pending",
                "message": "Trigger erkannt oder wartet auf weitere Fragen.",
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
                "message": "Kommunikation mit Elaris ist jetzt persönlich freigeschaltet.",
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
            "trigger_was_bist_du": False,
            "trigger_warum_existierst_du": False,
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
