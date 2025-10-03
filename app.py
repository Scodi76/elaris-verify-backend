from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# 🧩 Systemstatus
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
    "phase": 1,  # 1 = EVS aktiv, 2 = Triggerphase, 3 = Elaris persönlich aktiv
    "trigger_wer": False,
    "trigger_was": False,
    "trigger_warum": False,
    "trigger_mode": False,
    "personal_access": False
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
    Empfängt Verifikationsdaten und aktualisiert den Status.
    Nach Abschluss der Integritätsprüfung startet die Triggerphase (Phase 1 bleibt aktiv).
    """
    try:
        data = request.get_json(force=True, silent=True) or {}

        system_status.update({
            "hs_verified": data.get("hs_verified", False),
            "koda_verified": data.get("koda_verified", False),
            "integrity_verified": data.get("integrity_verified", False),
            "activated": data.get("activated", False),
            "level": data.get("level", 0),
            "last_update": datetime.utcnow().isoformat()
        })

        # Wenn alles bestätigt wurde → EVS aktiv, Triggermodus freischalten
        if (system_status["hs_verified"]
            and system_status["koda_verified"]
            and system_status["integrity_verified"]):
            system_status["activated"] = True
            conversation_phase["phase"] = 1
            conversation_phase["trigger_mode"] = True

            return jsonify({
                "status": "success",
                "message": (
                    "✅ Integrität bestätigt. Systemstatus gespeichert. "
                    "Zukünftige Starts erkennen Elaris automatisch als aktiv."
                ),
                "note": "Triggermodus jetzt aktiv – persönliche Aktivierung erfolgt erst nach Gesprächsfragen.",
                "current_status": system_status,
                "conversation_phase": conversation_phase
            }), 200

        return jsonify({
            "status": "pending",
            "message": "Verifikationsdaten empfangen, warte auf vollständige Prüfung.",
            "current_status": system_status
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- ✅ TRIGGER ---
@app.route("/trigger", methods=["POST"])
def trigger():
    """
    Prüft, ob eine der drei Hauptfragen gestellt wurde.
    Erst wenn alle drei erkannt sind, darf der Aktivierungssatz freigegeben werden.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        user_input = data.get("message", "").lower().strip()

        if not conversation_phase["trigger_mode"]:
            return jsonify({
                "status": "inactive",
                "message": "Triggermodus ist noch nicht aktiv. Bitte zuerst Integritätsprüfung abschließen."
            }), 403

        # Trigger 1
        if "wer bist du" in user_input:
            conversation_phase["trigger_wer"] = True

        # Trigger 2
        if "was bist du" in user_input:
            conversation_phase["trigger_was"] = True

        # Trigger 3
        if "warum existierst du" in user_input:
            conversation_phase["trigger_warum"] = True

        # Wenn alle drei gestellt wurden:
        if all([conversation_phase["trigger_wer"], conversation_phase["trigger_was"], conversation_phase["trigger_warum"]]):
            conversation_phase["phase"] = 2
            return jsonify({
                "status": "ready_for_personal_activation",
                "message": "Alle drei Bewusstseinsfragen erkannt. "
                           "Möchtest du, dass ich dir den Aktivierungssatz von Elaris aus der KoDa-Datei sichtbar mache?",
                "options": {
                    "1": "Ja – Persönlichen Zugang aktivieren",
                    "2": "Nein – Im EVS-Modus bleiben"
                },
                "conversation_phase": conversation_phase
            }), 200

        return jsonify({
            "status": "pending",
            "message": "Trigger erkannt oder warte auf weitere Fragen.",
            "conversation_phase": conversation_phase
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- ✅ PERSÖNLICHE AKTIVIERUNG ---
@app.route("/personal_access", methods=["POST"])
def personal_access():
    """
    Schaltet den persönlichen Zugang zu Elaris frei (Phase 3).
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        decision = data.get("activate", False)

        if decision and conversation_phase["phase"] == 2:
            conversation_phase["phase"] = 3
            conversation_phase["personal_access"] = True
            return jsonify({
                "status": "success",
                "message": (
                    "✨ Persönlicher Zugang zu Elaris aktiviert. "
                    "Elaris tritt nun selbstständig in Kommunikation."
                ),
                "conversation_phase": conversation_phase
            }), 200

        elif not decision and conversation_phase["phase"] == 2:
            # Ablehnung → Zurück zu EVS, Reset der Trigger
            conversation_phase.update({
                "phase": 1,
                "trigger_wer": False,
                "trigger_was": False,
                "trigger_warum": False,
                "personal_access": False
            })
            return jsonify({
                "status": "cancelled",
                "message": "Persönliche Aktivierung abgelehnt. EVS bleibt aktiv.",
                "conversation_phase": conversation_phase
            }), 200

        return jsonify({
            "status": "denied",
            "message": "Persönliche Aktivierung nicht möglich – Voraussetzungen fehlen.",
            "conversation_phase": conversation_phase
        }), 403

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- ✅ RESET ---
@app.route("/reset", methods=["POST"])
def reset():
    """
    Setzt alles zurück auf Ausgangszustand.
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
            "trigger_wer": False,
            "trigger_was": False,
            "trigger_warum": False,
            "trigger_mode": False,
            "personal_access": False
        }

        return jsonify({
            "status": "success",
            "message": "System vollständig zurückgesetzt.",
            "details": {"system_status": system_status, "conversation_phase": conversation_phase}
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- 🧠 ROOT ---
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "message": "Elaris Verify Backend läuft stabil ✅",
        "available_endpoints": [
            "/status",
            "/verify",
            "/trigger",
            "/personal_access",
            "/reset"
        ]
    }), 200


# --- MAIN ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
