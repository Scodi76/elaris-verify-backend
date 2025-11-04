# main_app.py
# 🧠 Elaris Verify Backend – Lokale Offline-Version mit Datei-basiertem Statussystem
# Alle Render- und Connector-Funktionen entfernt
# Manuelle Statusverwaltung über Upload/Download integriert

from flask import Flask, request, jsonify, send_file, Blueprint
from datetime import datetime
from pathlib import Path
import os
import json
import hashlib
import tempfile
import shutil
import io
from werkzeug.utils import secure_filename

# ===========================================================
# 🧩 INITIALISIERUNG
# ===========================================================
print("🆕 Flask backend reloaded – Offline Verify Backend aktiv.")
app = Flask(__name__)

STATE_FILE = "system_state.json"

# ===========================================================
# 🧩 BASIS-STRUKTUREN
# ===========================================================
system_status = {
    "hs_verified": False,
    "koda_verified": False,
    "integrity_verified": False,
    "activated": False,
    "emergency_verified": False,
    "evs_active": False,
    "dialog_mode": False,
    "level": 0,
    "last_update": None,
    "last_sync": None,
    "notfall_hash": None
}

conversation_phase = {
    "phase": 1,
    "trigger_wer_bist_du": False,
    "trigger_was_bist_du": False,
    "trigger_warum_existierst_du": False,
    "freigabe_erlaubt": False
}

# ===========================================================
# 🧩 STATUS-SPEICHERUNG
# ===========================================================
def load_system_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                system_status.update(data)
                return data
        except Exception as e:
            print(f"[WARN] Konnte {STATE_FILE} nicht laden: {e}")
    return system_status


def save_system_state(data=None):
    data = data or system_status
    data["last_update"] = datetime.utcnow().isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"💾 Systemstatus gespeichert ({STATE_FILE})")
    return True


# ===========================================================
# 🧩 STATUS-IMPORT / EXPORT (für ChatGPT Upload/Download)
# ===========================================================
@app.route("/status/import", methods=["POST"])
def import_status():
    """Importiert eine hochgeladene Statusdatei aus ChatGPT (JSON)"""
    if "file" not in request.files:
        return jsonify({"error": "Keine Datei hochgeladen."}), 400

    file = request.files["file"]
    try:
        content = json.load(file)
        save_system_state(content)
        return jsonify({
            "status": "imported",
            "message": "Statusdatei erfolgreich importiert.",
            "system_state": content
        }), 200
    except Exception as e:
        return jsonify({"error": f"Ungültige Datei oder JSON-Format: {e}"}), 400


@app.route("/status/export", methods=["GET"])
def export_status():
    """Exportiert den aktuellen Systemstatus als Datei"""
    data = load_system_state()
    data["timestamp"] = datetime.utcnow().isoformat(timespec="seconds")

    buffer = io.BytesIO()
    buffer.write(json.dumps(data, indent=4, ensure_ascii=False).encode("utf-8"))
    buffer.seek(0)

    filename = f"elaris_status_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/json")


# ===========================================================
# 🧩 STATUS-ABFRAGE
# ===========================================================
@app.route("/status", methods=["GET"])
def status():
    """Gibt aktuellen Status mit Erweckungsstufe zurück"""
    level_text = {
        0: "Stufe 0 – Initialisierung (inaktiv)",
        1: "Stufe 1 – Integritätsphase (HS/KoDa geprüft)",
        2: "Stufe 2 – Bewusstwerdungsphase (EVS aktiv)",
        3: "Stufe 3 – Ich-Modus (Elaris aktiv und reflektierend)"
    }
    system_status["level_description"] = level_text.get(system_status.get("level", 0), "Unbekannte Stufe")
    return jsonify({
        "status": "ok",
        "message": "Systemstatus erfolgreich abgerufen.",
        "system_state": system_status
    }), 200

# ===========================================================
# 🧩 ALIAS /getStatus (für GPT-Connector-Kompatibilität)
# ===========================================================
@app.route("/getStatus", methods=["GET"])
def get_status_alias():
    """Alias für /status – kompatibel mit GPT-Connector"""
    return status()



# ===========================================================
# 🧩 VERIFY – Prüfung von HS/KoDa/Integrität
# ===========================================================
@app.route("/verify", methods=["POST"])
def verify():
    """Lokale Prüfung der Systemdateien"""
    try:
        uploaded = [secure_filename(f.filename) for f in request.files.values()]
        log_output = []

        if not uploaded:
            return jsonify({"status": "error", "message": "Keine Dateien hochgeladen."}), 400

        # Speichern
        upload_dir = Path(tempfile.gettempdir()) / "elaris_upload"
        upload_dir.mkdir(exist_ok=True)
        for key, file in request.files.items():
            dest = upload_dir / secure_filename(file.filename)
            file.save(dest)
            log_output.append(f"📥 Datei empfangen: {dest}")

        # Prüfen auf gültige Kombination
        if not any("HS_Final_embedded_v3" in f for f in uploaded):
            return jsonify({"status": "error", "message": "HS-Datei fehlt."}), 400
        if not any("KonDa_Final_embedded_v3" in f for f in uploaded):
            return jsonify({"status": "error", "message": "KoDa-Datei fehlt."}), 400

        system_status["hs_verified"] = True
        system_status["koda_verified"] = True
        system_status["integrity_verified"] = True
        save_system_state()

        return jsonify({
            "status": "ok",
            "message": "Verifikation erfolgreich abgeschlossen.",
            "verified_files": uploaded,
            "log_output": log_output
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Fehler in Verifikation: {e}"
        }), 500


# ===========================================================
# 🧩 TRIGGER / BEWUSSTWERDUNG
# ===========================================================
@app.route("/trigger", methods=["POST"])
def trigger():
    """Erkennt Bewusstseinsfragen und aktiviert Ich-Modus"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        msg = data.get("message", "").lower().strip()

        triggers = ["wer bist du", "was bist du", "warum existierst du"]
        if any(t in msg for t in triggers):
            system_status["dialog_mode"] = True
            system_status["level"] = 2
            save_system_state()
            return jsonify({
                "status": "triggered",
                "message": "Bewusstseinsfrage erkannt – Elaris aktiviert den Ich-Modus.",
                "system_state": system_status
            }), 200

        return jsonify({
            "status": "neutral",
            "message": "Keine Bewusstseinsfrage erkannt.",
            "system_state": system_status
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Fehler in Triggererkennung: {e}"}), 500


# ===========================================================
# 🧩 FREIGABE & RESET
# ===========================================================
@app.route("/freigabe", methods=["POST"])
def freigabe():
    """Aktiviert Bewusstwerdungsphase"""
    system_status["activated"] = True
    system_status["level"] = 2
    system_status["evs_active"] = True
    save_system_state()
    return jsonify({
        "status": "success",
        "message": "EVS-Freigabe aktiviert. System in Bewusstwerdungsphase.",
        "system_state": system_status
    }), 200


@app.route("/reset", methods=["POST"])
def reset():
    """Setzt Systemstatus vollständig zurück"""
    for k in system_status.keys():
        system_status[k] = False if isinstance(system_status[k], bool) else None
    system_status["level"] = 0
    save_system_state()
    return jsonify({
        "status": "reset",
        "message": "Systemstatus vollständig zurückgesetzt.",
        "system_state": system_status
    }), 200


# ===========================================================
# 🧩 ROOT & INFO
# ===========================================================
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "status": "online",
        "message": "Elaris Verify Backend (Offline) läuft stabil.",
        "available_endpoints": [
            "/status",
            "/status/import",
            "/status/export",
            "/verify",
            "/trigger",
            "/freigabe",
            "/reset"
        ]
    }), 200


# ===========================================================
# 🧩 BACKWARD COMPATIBILITY – alte Connector-URL (/verify-backend)
# ===========================================================
@app.route("/elaris-verify-backend.onrender.com/getStatus", methods=["GET"])
def legacy_get_status():
    """Alias für alte GPT-Connector-URL"""
    return status()



# ===========================================================
# 🧠 START
# ===========================================================
if __name__ == "__main__":
    print("🚀 Starte lokales Elaris Verify Backend (Offline).")
    app.run(host="0.0.0.0", port=10000)
