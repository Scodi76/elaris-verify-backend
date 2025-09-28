from flask import Flask, request, jsonify
import json, os
from datetime import datetime

app = Flask(__name__)

DATA_FILE = "verify_storage.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"hs_verified": False, "koda_verified": False, "last_update": None}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "Elaris Verify Backend",
        "status": "online",
        "version": "1.0",
        "info": "Backend zur Speicherung und Prüfung der Elaris-Freigabe"
    })

@app.route("/status", methods=["GET"])
def get_status():
    return jsonify(load_data())

@app.route("/verify", methods=["POST"])
def update_status():
    data = load_data()
    body = request.get_json(force=True)

    if "hs_verified" in body:
        data["hs_verified"] = body["hs_verified"]
    if "koda_verified" in body:
        data["koda_verified"] = body["koda_verified"]

    data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    return jsonify({"message": "Status aktualisiert", "new_state": data})

@app.route("/reset", methods=["POST"])
def reset_status():
    data = {"hs_verified": False, "koda_verified": False, "last_update": None}
    save_data(data)
    return jsonify({"message": "Zurückgesetzt", "new_state": data})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
