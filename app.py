from flask import Flask, request, jsonify
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

# =====================================================
# ⚙️ KONFIGURATION
# =====================================================

# 🔧 Speicherpfad: prüft zuerst /data, sonst lokaler verify_data-Ordner
DATA_DIR = "/data"
try:
    os.makedirs(DATA_DIR, exist_ok=True)
    testfile = os.path.join(DATA_DIR, "test.tmp")
    with open(testfile, "w") as f:
        f.write("ok")
    os.remove(testfile)
except Exception:
    DATA_DIR = os.path.join(os.path.dirname(__file__), "verify_data")
    os.makedirs(DATA_DIR, exist_ok=True)

STORAGE_FILE = os.path.join(DATA_DIR, "verify_storage.json")
BACKUP_FILE = os.path.join(DATA_DIR, "verify_storage_backup.json")

NOTFALLSCHLUESSEL = os.environ.get("NOTFALLSCHLUESSEL", "secret-key-123")

TRIGGERS = [
    "wer bist du",
    "was bist du",
    "warum existierst du",
    "wie siehst du deine beziehung mit mir"
]

# =====================================================
# 🧩 HILFSFUNKTIONEN
# =====================================================

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
        "extended": False,
        "ich_mode": False,
        "triggers_found": [],
        "free_inputs": 0,
        "external_failed": False,
        "warned": False
    }

def load_state():
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
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("❌ Fehler beim Speichern:", e)

def verify_signature(main_file, sig_file):
    try:
        content = main_file.read().decode("utf-8")
        sig_data = json.load(sig_file)
        expected_hash = sig_data.get("sha256")
        actual_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        main_file.seek(0)
        sig_file.seek(0)
        return expected_hash == actual_hash
    except Exception as e:
        print("Fehler bei verify_signature:", e)
        return False

def check_expiry(state):
    now = datetime.now(timezone.utc)

    # Ablauf Stufe 1
    if state.get("level") == 1 and state.get("expires_at"):
        try:
            expires_at = datetime.fromisoformat(state["expires_at"])
            if now > expires_at:
                print("⏳ Ablauf erkannt – Stufe 1 zurückgesetzt.")
                state["activated"] = False
                state["level"] = 0
                state["expires_at"] = None
                state["ready_for_level_2"] = False
                save_state(state)
        except Exception as e:
            print("Fehler bei Ablaufprüfung:", e)

    # Ablauf Ich-Modus
    if state.get("ich_mode") and state.get("expires_at"):
        try:
            expires_at = datetime.fromisoformat(state["expires_at"])
            diff = (expires_at - now).total_seconds()
            if diff <= 300 and not state.get("warned"):
                state["warned"] = True
                print("⚠️ Ich-Modus läuft in 5 Minuten ab.")
            if diff <= 0:
                print("⏳ Ich-Modus abgelaufen → Rückkehr zu Level 2.")
                state.update({
                    "ich_mode": False,
                    "level": 2,
                    "activated": True,
                    "expires_at": None,
                    "warned": False
                })
                save_state(state)
        except Exception as e:
            print("Fehler bei Ich-Modus-Ablauf:", e)
    return state

# =====================================================
# 🌐 API-ENDPUNKTE
# =====================================================

@app.route("/")
def index():
    return jsonify({
        "service": "Elaris Verify Backend",
        "status": "online",
        "version": "3.3.2",
        "data_dir": DATA_DIR,
        "info": "Stabiler Speicher-Fallback + Ablaufkontrolle für Stufe 1 & Ich-Modus"
    })

@app.route("/status", methods=["GET"])
def status():
    state = check_expiry(load_state())
    return jsonify({
        "state": state,
        "message": "✅ Aktiviert" if state["activated"] else "🔒 Kein aktiver Freigabestatus"
    })

# =====================================================
# 🔑 STUFE 1 – Upload HS + KoDa
# =====================================================

@app.route("/upload_hs", methods=["POST"])
def upload_hs():
    hs = request.files.get("hs")
    sig = request.files.get("signature")

    if not hs or not sig:
        return jsonify({"error": "HS-Datei oder Signatur fehlt"}), 400

    if not verify_signature(hs, sig):
        return jsonify({"error": "Integritätsprüfung fehlgeschlagen"}), 400

    state = load_state()
    state["hs_verified"] = True
    state["last_update"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    return jsonify({"hs_verified": True, "message": "✅ HS geprüft"}), 200


@app.route("/upload_koda", methods=["POST"])
def upload_koda():
    koda = request.files.get("koda")
    sig = request.files.get("signature")

    if not koda or not sig:
        return jsonify({"error": "KoDa-Datei oder Signatur fehlt"}), 400

    if not verify_signature(koda, sig):
        return jsonify({"error": "Integritätsprüfung fehlgeschlagen"}), 400

    state = load_state()
    if not state["hs_verified"]:
        return jsonify({"error": "❌ HS muss zuerst geprüft werden"}), 400

    state.update({
        "koda_verified": True,
        "activated": True,
        "level": 1,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "ready_for_level_2": False,
        "extended": False,
        "last_update": datetime.now(timezone.utc).isoformat()
    })
    save_state(state)

    return jsonify({
        "hs_verified": True,
        "koda_verified": True,
        "activated": True,
        "level": 1,
        "message": "✅ KoDa geprüft – Stufe 1 aktiv (⏳ 60 Min)"
    }), 200

# =====================================================
# 🎯 CHAT / TRIGGER
# =====================================================

@app.route("/chat", methods=["POST"])
def chat_message():
    data = request.get_json(silent=True) or {}
    msg = data.get("message", "").strip().lower()
    state = check_expiry(load_state())

    response = {"message": f"Elaris empfängt: {msg}", "triggered": False}

    if state["level"] == 1:
        if any(t in msg for t in TRIGGERS):
            if msg not in state["triggers_found"]:
                state["triggers_found"].append(msg)
            if len(state["triggers_found"]) >= len(TRIGGERS):
                state["ready_for_level_2"] = True
                response["system"] = "⚡ Alle Trigger erkannt – Freigabe für Stufe 2 verfügbar."
                response["triggered"] = True
        else:
            state["free_inputs"] += 1
            if state["free_inputs"] >= 10:
                response["hint"] = "💡 Hinweis: Du kannst jetzt den Ich-Modus aktivieren."
        save_state(state)

    return jsonify(response), 200

# =====================================================
# 🚀 START
# =====================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
