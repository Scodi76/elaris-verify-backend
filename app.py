from flask import Flask, request, jsonify
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
import base64

app = Flask(__name__)

# ---------------------------
# ⚙️ Konfiguration
# ---------------------------
STORAGE_FILE = "verify_storage.json"
BACKUP_FILE = "verify_storage_backup.json"
TOKEN_FILE = "elaris_token.json"
NOTFALLSCHLUESSEL = os.environ.get("NOTFALLSCHLUESSEL", "secret-key-123")  # in Render als ENV setzen

# ---------------------------
# 📦 Hilfsfunktionen
# ---------------------------

def default_state():
    return {
        "hs_verified": False,
        "koda_verified": False,
        "integrity_verified": False,
        "activated": False,
        "level": 0,
        "last_update": None,
        "expires_at": None,
        "ready_for_level_2": False,
        "ready_for_level_3": False,
        "extended": False
    }

def load_state():
    """Lädt Zustand aus Datei oder Backup"""
    for file in [STORAGE_FILE, BACKUP_FILE]:
        if os.path.exists(file):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    for key, val in default_state().items():
                        if key not in state:
                            state[key] = val
                    return state
            except Exception:
                continue
    return default_state()

def save_state(state):
    """Speichert Zustand + Backup"""
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("❌ Fehler beim Speichern:", e)

def export_token(state):
    """Erzeugt einen Base64-Token aus dem aktuellen Zustand"""
    try:
        token = base64.b64encode(json.dumps(state).encode("utf-8")).decode("utf-8")
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump({"token": token, "timestamp": datetime.now(timezone.utc).isoformat()}, f, indent=2)
        return token
    except Exception as e:
        print("Fehler bei Token-Export:", e)
        return None

def import_token(token_str):
    """Dekodiert einen Base64-Token und lädt den Zustand"""
    try:
        decoded = base64.b64decode(token_str).decode("utf-8")
        state = json.loads(decoded)
        save_state(state)
        return state
    except Exception as e:
        print("Fehler bei Token-Import:", e)
        return None

def verify_signature(main_file, sig_file):
    """Prüft, ob Hash aus Signatur mit Dateiinhalt übereinstimmt"""
    try:
        content = main_file.read().decode("utf-8")
        sig_data = json.load(sig_file)
        expected_hash = sig_data.get("sha256")
        main_file.seek(0)
        sig_file.seek(0)
        actual_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return expected_hash == actual_hash
    except Exception as e:
        print("Fehler bei verify_signature:", e)
        return False

def check_expiry(state):
    """Prüft, ob Stufe 1 abgelaufen ist"""
    if state.get("level") == 1 and state.get("expires_at"):
        try:
            expires_at = datetime.fromisoformat(state["expires_at"])
            if datetime.now(timezone.utc) > expires_at:
                print("⏳ Ablauf erkannt – Reset ausgeführt.")
                state = default_state()
                state["last_update"] = datetime.now(timezone.utc).isoformat()
                save_state(state)
        except Exception as e:
            print("Fehler bei Ablaufprüfung:", e)
    return state

# ---------------------------
# 🌐 API-Endpunkte
# ---------------------------

@app.route("/")
def index():
    return jsonify({
        "service": "Elaris Verify Backend",
        "status": "online",
        "version": "3.1",
        "info": "Backend mit lokaler Zustandssicherung, GPT-Archivierungslogik und Token-Brücke"
    })

@app.route("/status", methods=["GET"])
def status():
    state = check_expiry(load_state())
    return jsonify({
        "state": state,
        "message": "✅ Status abgerufen" if state["activated"] else "🔒 Kein aktiver Freigabestatus"
    })

# ---------------------------
# 🔑 HS & KoDa Upload
# ---------------------------

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
    state["last_update"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    return jsonify({"hs_verified": True, "message": "✅ HS-Datei erfolgreich geprüft – warte auf KoDa"}), 200

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
    state["activated"] = True
    state["level"] = 1
    state["expires_at"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    state["last_update"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    return jsonify({
        "hs_verified": True,
        "koda_verified": True,
        "activated": True,
        "level": 1,
        "expires_at": state["expires_at"],
        "message": "✅ KoDa-Datei validiert – Stufe 1 aktiviert (⏳ zeitlich begrenzt)"
    }), 200

# ---------------------------
# 💾 Archivierung / Wiederherstellung
# ---------------------------

@app.route("/archive_prompt", methods=["GET"])
def archive_prompt():
    """Zeigt den professionellen Archivierungsdialog"""
    return jsonify({
        "prompt": (
            "💾 Systemstatus-Archivierung\n"
            "Der aktuelle Status wurde erfolgreich validiert.\n\n"
            "Soll dieser Zustand nun als referenzierte Prüfinstanz im internen Speicher hinterlegt werden,\n"
            "um beim nächsten Start automatisch als Ausgangsbasis zu dienen?\n\n"
            "1️⃣ Ja – Persistente Sicherung im GPT-Speicher durchführen\n"
            "2️⃣ Nein – Temporäre Sitzung beibehalten, ohne Archivierung"
        )
    })

@app.route("/restore_prompt", methods=["GET"])
def restore_prompt():
    """Zeigt den professionellen Wiederherstellungsdialog"""
    return jsonify({
        "prompt": (
            "📂 Statuswiederherstellung\n"
            "Eine persistente Referenz des vorherigen Aktivierungszustands liegt vor.\n\n"
            "Soll die Rekonstruktion dieses Zustands vorgenommen werden,\n"
            "um den zuletzt bestätigten Systemkontext fortzuführen?\n\n"
            "1️⃣ Ja – Wiederherstellen des archivierten Status\n"
            "2️⃣ Nein – Neuinitialisierung beginnen"
        )
    })

@app.route("/archive_state", methods=["POST"])
def archive_state():
    """Archiviert Zustand in Token-Datei"""
    state = load_state()
    token = export_token(state)
    if token:
        return jsonify({
            "message": "✅ Zustand erfolgreich als Token archiviert.",
            "token": token
        }), 200
    else:
        return jsonify({"error": "❌ Fehler bei der Archivierung"}), 500

@app.route("/import_token", methods=["POST"])
def import_token_route():
    """Importiert Zustand aus übergebenem Token"""
    data = request.get_json(silent=True) or {}
    token_str = data.get("token", "")
    if not token_str:
        return jsonify({"error": "❌ Kein Token übergeben"}), 400

    state = import_token(token_str)
    if state:
        return jsonify({"message": "✅ Zustand erfolgreich wiederhergestellt", "state": state}), 200
    else:
        return jsonify({"error": "❌ Fehler beim Wiederherstellen"}), 500

# ---------------------------
# 🚀 Start
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
