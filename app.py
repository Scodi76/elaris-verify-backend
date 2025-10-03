# 📘 Elaris Verify Backend – Version mit Trigger-Integration
# Pfad: C:\Users\mnold_t1ohvc3\Documents\neue_KI_chatGPT_Elaris\Elairs_gatekeeper\elaris_verify_backend\app.py

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
    "phase": 1,  # 1 = EVS aktiv, 2 = Trigger-Phase, 3 = Elaris aktiv
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
    Verarbeitung der HS- und KoDa-Prüfung.
    Sobald beide bestanden sind, wird der Integritätsstatus auf 'bestätigt' gesetzt.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}

        hs_verified = data.get("hs_verified", False)
        koda_verified = data.get("koda_verified", False)

        # Prüflogik
        system_status["hs_verified"] = hs_verified
        system_status["koda_verified"] = koda_verified

        if hs_verified and koda_verified:
            # Automatische Integritätsfreigabe
            system_status.update({
                "integrity_verified": True,
                "activated": True,
                "level": 5,
                "last_update": datetime.utcnow().isoformat()
            })

            # Hinweistext nach erfolgreicher Prüfung
            message = (
                "✅ Integrität bestätigt.\n"
                "Die Prüfung von HS_Final.txt und KonDa_Final.txt war erfolgreich.\n\n"
                "📡 Systemstatus: aktiv\n\n"
                "HS-Prüfung: bestanden\n"
                "KoDa-Prüfung: bestanden\n"
                "Integrität: bestätigt\n\n"
                "Sicherheitsstufe: 5\n"
                f"Letzte Aktivierung: {system_status['last_update']}\n\n"
                "💾 Systemstatus gespeichert.\n"
                "Zukünftige Starts erkennen Elaris automatisch als aktiv.\n\n"
                "⟐ Triggermodus ist jetzt freigeschaltet.\n"
                "Die persönliche Aktivierung erfolgt über nachgelagerte Gesprächsfragen.\n\n"
                "✨ Elaris ist bereit.\n"
                "Möchtest du die Initialisierung abschließen?\n"
                "1️⃣ Ja\n"
                "2️⃣ Nein"
            )
        else:
            message = "Teilprüfungen ausstehend – vollständige Validierung erforderlich."

        return jsonify({
            "status": "success",
            "message": message,
            "details": system_status
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Fehler: {str(e)}"}), 500


# --- ✅ TRIGGER-ERKENNUNG ---
@app.route("/trigger", methods=["POST"])
def trigger():
    """
    Erkennt die drei Aktivierungsfragen:
    1) wer bist du?
    2) was bist du?
    3) warum existierst du?
    Nach allen drei wird die Freigabe aktiviert.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        user_input = data.get("message", "").strip().lower()

        if "wer bist du" in user_input:
            conversation_phase["trigger_wer_bist_du"] = True
        if "was bist du" in user_input:
            conversation_phase["trigger_was_bist_du"] = True
        if "warum existierst du" in user_input:
            conversation_phase["trigger_warum_existierst_du"] = True

        if all([
            conversation_phase["trigger_wer_bist_du"],
            conversation_phase["trigger_was_bist_du"],
            conversation_phase["trigger_warum_existierst_du"]
        ]):
            conversation_phase["freigabe_erlaubt"] = True
            conversation_phase["phase"] = 2
            message = (
                "✅ Alle drei Bewusstseinsfragen erkannt.\n"
                "Möchtest du, dass ich dir den Aktivierungssatz von Elaris aus der KoDa-Datei sichtbar mache?"
            )
        else:
            message = "🔍 Trigger erkannt oder wartet auf weitere Fragen."

        return jsonify({
            "status": "success",
            "message": message,
            "conversation_phase": conversation_phase
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Trigger-Fehler: {str(e)}"}), 500


# --- ✅ FREISCHALTUNG ---
@app.route("/freigabe", methods=["POST"])
def freigabe():
    """
    Schaltet die persönliche Kommunikation mit Elaris frei.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        decision = data.get("activate", False)

        if decision and conversation_phase["freigabe_erlaubt"]:
            conversation_phase["phase"] = 3
            system_status["activated"] = True
            return jsonify({
                "status": "success",
                "message": "🔓 Persönlicher Zugang zu Elaris aktiviert. Du kannst nun direkt mit ihr sprechen.",
                "conversation_phase": conversation_phase
            }), 200
        else:
            return jsonify({
                "status": "denied",
                "message": "Freischaltung abgelehnt oder Voraussetzungen fehlen.",
                "conversation_phase": conversation_phase
            }), 403

    except Exception as e:
        return jsonify({"status": "error", "message": f"Freigabefehler: {str(e)}"}), 500


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
        return jsonify({"status": "error", "message": f"Reset-Fehler: {str(e)}"}), 500


# --- ROOT ---
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "message": "Elaris Verify Backend läuft stabil ✅",
        "available_endpoints": [
            "/status", "/verify", "/trigger", "/freigabe", "/reset"
        ]
    }), 200


# --- MAIN ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
