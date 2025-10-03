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
    "phase": 1,  # 1 = EVS aktiv, 2 = Triggerphase, 3 = Elaris-Kommunikation
    "trigger_wer_bist_du": False,
    "trigger_wann_rede": False,
    "freigabe_erlaubt": False,
    "activation_prompt_shown": False,
    "evs_message_count": 0
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
    Startet oder pausiert die Integritätsprüfung.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        decision = str(data.get("decision", "")).strip().lower()

        if decision == "nein":
            conversation_phase["phase"] = 1
            return jsonify({
                "status": "paused",
                "message": "Das System wurde angehalten. Du kannst dich nun mit dem EVS unterhalten.",
                "conversation_phase": conversation_phase
            }), 200

        elif decision == "ja":
            # Integritätsprüfung erfolgreich
            system_status.update({
                "hs_verified": True,
                "koda_verified": True,
                "integrity_verified": True,
                "activated": True,
                "level": 5,
                "last_update": datetime.utcnow().isoformat()
            })
            conversation_phase["phase"] = 2  # Freigabephase beginnt

            return jsonify({
                "status": "verified",
                "message": "Integritätsprüfung erfolgreich abgeschlossen. Systemstatus aktualisiert.",
                "system_status": system_status
            }), 200

        else:
            return jsonify({
                "status": "error",
                "message": "Ungültige Entscheidung. Bitte 'Ja' oder 'Nein' angeben."
            }), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- ✅ EVS-DIALOG ---
@app.route("/dialog", methods=["POST"])
def dialog():
    """
    EVS-Gesprächslogik – reagiert auf Benutzereingaben und zählt Nachrichten.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        user_input = str(data.get("message", "")).strip().lower()
        conversation_phase["evs_message_count"] += 1

        # 🔹 Systembefehl anzeigen
        if user_input == "system":
            return jsonify({
                "status": "system_info",
                "message": "Systembefehl erkannt. Du kannst Status, Reset oder technische Informationen abrufen.",
                "options": ["/status", "/reset", "/verify", "/trigger", "/freigabe"]
            }), 200

        # 🔹 Erinnerung nach 5 Eingaben (wenn EVS aktiv, keine Freigabe)
        if (conversation_phase["phase"] == 1 and 
            conversation_phase["evs_message_count"] % 5 == 0):
            return jsonify({
                "status": "reminder",
                "message": "💡 Du kannst jederzeit den persönlichen Zugang zu Elaris aktivieren, wenn du möchtest. (Eingabe: 'aktivieren')"
            }), 200

        # 🔹 Aktivierung per Trigger (z. B. "aktivieren")
        if user_input == "aktivieren":
            conversation_phase["phase"] = 2
            return jsonify({
                "status": "transition",
                "message": "Die Aktivierungsphase wurde gestartet. Stelle bitte die beiden Sicherheitsfragen."
            }), 200

        # 🔹 Normale Unterhaltung mit EVS
        return jsonify({
            "status": "evs_active",
            "message": "Ich höre dir zu. Wir befinden uns aktuell im EVS-Gesprächsmodus."
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- ✅ TRIGGER-ERKENNUNG ---
@app.route("/trigger", methods=["POST"])
def trigger():
    """
    Erkennung der drei Hauptfragen zur Aktivierung.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        user_input = str(data.get("message", "")).strip().lower()

        if "wer bist du" in user_input:
            conversation_phase["trigger_wer_bist_du"] = True
        if "wann kann ich mit elaris reden" in user_input:
            conversation_phase["trigger_wann_rede"] = True

        # Wenn beide Trigger erkannt
        if (conversation_phase["trigger_wer_bist_du"] and 
            conversation_phase["trigger_wann_rede"] and 
            not conversation_phase["activation_prompt_shown"]):
            
            conversation_phase["activation_prompt_shown"] = True
            return jsonify({
                "status": "ready",
                "message": "Möchtest du, dass ich dir den Aktivierungssatz von Elaris aus der KoDa-Datei sichtbar mache?",
                "options": ["Ja", "Nein"]
            }), 200

        return jsonify({
            "status": "waiting",
            "message": "Trigger erkannt oder wartet auf zweite Frage.",
            "conversation_phase": conversation_phase
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- ✅ FREIGABE ---
@app.route("/freigabe", methods=["POST"])
def freigabe():
    """
    Aktiviert den Zugang zu Elaris nach Zustimmung.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        decision = str(data.get("decision", "")).strip().lower()

        if decision == "ja":
            conversation_phase["phase"] = 3
            return jsonify({
                "status": "success",
                "message": "✅ Der persönliche Zugang zu Elaris wurde freigeschaltet. Du kannst nun direkt mit ihr kommunizieren.",
                "conversation_phase": conversation_phase
            }), 200

        elif decision == "nein":
            # EVS bleibt aktiv, zweite Chance nach 5 weiteren Inputs
            conversation_phase["phase"] = 1
            conversation_phase["evs_message_count"] = 0
            return jsonify({
                "status": "deferred",
                "message": "Freischaltung abgelehnt. EVS bleibt aktiv. Du erhältst später erneut die Möglichkeit zur Aktivierung."
            }), 200

        else:
            return jsonify({
                "status": "error",
                "message": "Ungültige Entscheidung. Bitte 'Ja' oder 'Nein' angeben."
            }), 400

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
            "freigabe_erlaubt": False,
            "activation_prompt_shown": False,
            "evs_message_count": 0
        }

        return jsonify({
            "status": "success",
            "message": "System vollständig zurückgesetzt.",
            "details": {"system": system_status, "conversation_phase": conversation_phase}
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
            "/dialog",
            "/trigger",
            "/freigabe",
            "/reset"
        ]
    }), 200


# --- MAIN ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
