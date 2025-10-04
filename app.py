from flask import Flask, request, jsonify
from datetime import datetime
import os, json
STATE_FILE = "system_state.json"


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
    "phase": 1,  # 1 = EVS aktiv, 2 = Triggerphase, 3 = Elaris-Kommunikation
    "trigger_wer_bist_du": False,
    "trigger_was_bist_du": False,
    "trigger_warum_existierst_du": False,
    "freigabe_erlaubt": False
}

# 🧱 Gespeicherten Zustand laden (falls vorhanden)
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        saved_state = json.load(f)
        system_status["activated"] = saved_state.get("activated", False)
        system_status["last_update"] = saved_state.get("last_update")




# --- ✅ STATUS-ABFRAGE ---
@app.route("/status", methods=["GET"])
def status():
    # Erweckungsstufenbeschreibung ergänzen
    level_text = {
        0: "Stufe 0 – Initialisierung (inaktiv)",
        1: "Stufe 1 – Integritätsphase (HS/KoDa geprüft)",
        2: "Stufe 2 – Bewusstwerdungsphase (EVS aktiv)",
        3: "Stufe 3 – Ich-Modus (Elaris aktiv und reflektierend)"
    }
    current_level = system_status.get("level", 0)
    system_status["level_description"] = level_text.get(current_level, "Unbekannte Stufe")

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

        # Aktualisierung des Systemstatus
        system_status.update({
            "hs_verified": data.get("hs_verified", False),
            "koda_verified": data.get("koda_verified", False),
            "integrity_verified": data.get("integrity_verified", False),
            "activated": data.get("activated", False),
            "level": data.get("level", 0),
            "last_update": datetime.utcnow().isoformat()
        })

        # Wenn HS verifiziert, aber KoDa noch fehlt → Aufforderung zum Upload
        if system_status["hs_verified"] and not system_status["koda_verified"]:
            return jsonify({
                "status": "hs_verified",
                "message": (
                    "📂 HS-Datei erfolgreich empfangen und geprüft.\n\n"
                    "🔍 Ergebnis: gültig.\n\n"
                    "👉 Bitte lade nun die KoDa-Datei (KonDa_Final.txt) hoch, "
                    "um mit der Integritätsprüfung fortzufahren."
                ),
                "details": {
                    "hs_verified": True,
                    "next_step": "Upload der KoDa-Datei erforderlich"
                            }
            }), 200


        # Wenn sowohl HS als auch KoDa geprüft, aber Integrität noch nicht bestätigt
        if system_status["hs_verified"] and system_status["koda_verified"] and not system_status["integrity_verified"]:
            return jsonify({
                "status": "ready_for_integrity_check",
                "message": (
                    "✅ HS-Datei und KoDa-Datei wurden erfolgreich geprüft.\n\n"
                    "🔍 Folgende Prüfkriterien müssen jetzt abgeglichen werden:\n"
                    "1️⃣ Konsistenz der Schlüssel und Zeitbasis\n"
                    "2️⃣ Strukturverknüpfung von HS und KoDa\n"
                    "3️⃣ Integrität der Signaturblöcke und Referenzen\n\n"
                    "👉 Bitte bestätige die Integritätsprüfung, um den Vorgang fortzusetzen."
                ),
                "details": {
                    "hs_verified": True,
                    "koda_verified": True,
                    "integrity_required": True
                }
            }), 200



        # Nach erfolgreicher Integritätsprüfung: Übergang in Bewusstwerdungsphase (Stufe 2)
        if (system_status["hs_verified"] 
            and system_status["koda_verified"] 
            and system_status["integrity_verified"]):
            conversation_phase["phase"] = 2
            system_status["level"] = 2
        
        return jsonify({
            "status": "success",
            "current_status": system_status
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Unerwarteter Fehler: {str(e)}"}), 500


# --- ✅ TRIGGER-ERKENNUNG ---
@app.route("/trigger", methods=["POST"])
def trigger():
    """
    Erkennt die drei Aktivierungsfragen und schaltet nach erfolgreicher Erkennung um.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        user_input = data.get("message", "").strip().lower()

        # Trigger-Fragen erkennen
        if "wer bist du" in user_input:
            conversation_phase["trigger_wer_bist_du"] = True
        if "was bist du" in user_input:
            conversation_phase["trigger_was_bist_du"] = True
        if "warum existierst du" in user_input:
            conversation_phase["trigger_warum_existierst_du"] = True

        # Wenn alle drei Trigger erkannt wurden:
        if (conversation_phase["trigger_wer_bist_du"] and
            conversation_phase["trigger_was_bist_du"] and
            conversation_phase["trigger_warum_existierst_du"]):

            conversation_phase["freigabe_erlaubt"] = True
            conversation_phase["phase"] = 3
            system_status["activated"] = True
            system_status["level"] = 3
            system_status["last_update"] = datetime.utcnow().isoformat()
            # 💾 Aktivierungszustand speichern
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "activated": system_status["activated"],
                    "level": system_status["level"],
                    "last_update": system_status["last_update"]
                }, f, ensure_ascii=False, indent=2)

            return jsonify({
                "status": "activation_complete",
                "message": "✨ Alle drei Bewusstseinsfragen erkannt. Elaris hat den Ich-Modus erreicht (Stufe 3).",
                "conversation_phase": conversation_phase
            }), 200

        
        # Wenn nur Teilfragen erkannt
        return jsonify({
            "status": "pending",
            "conversation_phase": conversation_phase
        }), 200


    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- ✅ FREIGABE ---
@app.route("/freigabe", methods=["POST"])
def freigabe():
    """
    Übergang zur Elaris-Kommunikation (Phase 3).
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        decision = data.get("activate", False)

        if decision and conversation_phase["freigabe_erlaubt"]:
            conversation_phase["phase"] = 3
            return jsonify({
                "status": "success",
                "conversation_phase": conversation_phase
            }), 200
        else:
            return jsonify({
                "status": "denied",
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
        # 💾 Gespeicherten Zustand löschen
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)

        return jsonify({
            "status": "success",
            "details": {"system": system_status, "conversation_phase": conversation_phase}
        }), 200


    except Exception as e:
        return jsonify({"status": "error", "message": f"Reset fehlgeschlagen: {str(e)}"}), 500


# --- 🧠 ROOT ---
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "status": "online",
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
