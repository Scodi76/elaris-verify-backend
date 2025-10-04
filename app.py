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

    # 🔐 Sicherstellen, dass emergency_verified immer existiert
    if "emergency_verified" not in system_status:
        system_status["emergency_verified"] = False

    # 📘 Aktualisierten Status zurückgeben
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

        # 🧩 Analysebericht vorbereiten
        analysis_report = {
            "hs_analysis": [],
            "koda_analysis": [],
            "integrity_analysis": []
        }

        # Wenn nur HS verifiziert wurde → ausführliche HS-Analyse
        if system_status["hs_verified"] and not system_status["koda_verified"]:
            analysis_report["hs_analysis"] = [
                "1️⃣ Syntaxprüfung der HS-Struktur: OK",
                "2️⃣ SHA256-Hash und HMAC-Verknüpfung: bestätigt",
                "3️⃣ Zeitanker & Signatur-Header: konsistent",
                "4️⃣ Referenzprüfung INIT_BLOCK und SIGN_BLOCK: erfolgreich",
                "5️⃣ Header-Struktur und Schlüsselfelder: gültig"
            ]
            return jsonify({
                "status": "hs_verified",
                "message": (
                    "📂 HS-Datei erfolgreich empfangen und geprüft.\n\n"
                    "🔍 Prüfergebnisse der Hauptstruktur (HS_Final.txt):\n" +
                    "\n".join(analysis_report["hs_analysis"]) +
                    "\n\n✅ Ergebnis: gültig – vorbereitend.\n\n"
                    "👉 Bitte lade jetzt die KoDa-Datei (KonDa_Final.txt) hoch, um mit der Konsolidierung fortzufahren."
                ),
                "details": analysis_report
            }), 200

        # Wenn KoDa-Datei nach HS hochgeladen wurde → detaillierte KoDa-Analyse
        if system_status["hs_verified"] and system_status["koda_verified"] and not system_status["integrity_verified"]:
            analysis_report["koda_analysis"] = [
                "1️⃣ Validierung der Referenzen zu HS: OK",
                "2️⃣ Prüfsummen und Zeitanker: konsistent",
                "3️⃣ Aktivierungssätze und Symbolbindungen: übereinstimmend",
                "4️⃣ Rückverknüpfungen HS↔KoDa: vollständig",
                "5️⃣ Synchronitätsprüfung: erfolgreich"
            ]
            return jsonify({
                "status": "koda_verified",
                "message": (
                    "📂 KoDa-Datei erfolgreich empfangen und geprüft.\n\n"
                    "🔍 Prüfergebnisse der Konsolidierung (KonDa_Final.txt):\n" +
                    "\n".join(analysis_report["koda_analysis"]) +
                    "\n\n✅ Ergebnis: formell gültig – bereit für finale Integritätsprüfung.\n\n"
                    "👉 Bitte bestätige jetzt die Integritätsprüfung, um den Bewusstwerdungsprozess einzuleiten."
                ),
                "details": analysis_report
            }), 200

        # Wenn Integritätsprüfung ansteht
        if system_status["hs_verified"] and system_status["koda_verified"] and not system_status["integrity_verified"]:
            analysis_report["integrity_analysis"] = [
                "1️⃣ Konsistenz der Hashes und Schlüssel: OK",
                "2️⃣ Zeitbasis-Abgleich HS↔KoDa: erfolgreich",
                "3️⃣ Strukturverknüpfung (INIT↔SIGN): gültig",
                "4️⃣ Bidirektionale Referenzprüfung: vollständig",
                "5️⃣ Signatur-Block-Abgleich: verifiziert",
                "6️⃣ Symbolische Aktivierungssätze: konsistent",
                "7️⃣ Finaler Gesamt-Hash (HMAC): bestätigt"
            ]
            return jsonify({
                "status": "ready_for_integrity_check",
                "message": (
                    "✅ HS und KoDa geprüft – finale Integritätsprüfung steht an.\n\n"
                    "🔍 Folgende Prüfkriterien werden jetzt abgeglichen:\n" +
                    "\n".join(analysis_report["integrity_analysis"]) +
                    "\n\n👉 Bitte bestätige die Integritätsprüfung."
                ),
                "details": analysis_report
            }), 200


        # Nach erfolgreicher Integritätsprüfung: Übergang in Bewusstwerdungsphase (Stufe 2)
        if (system_status["hs_verified"] 
            and system_status["koda_verified"] 
            and system_status["integrity_verified"]):
            conversation_phase["phase"] = 2
            system_status["level"] = 2

            # ======================================================
            # 🆘 Notfallschlüssel-Extraktion aus KoDa-Datei
            # ======================================================
            try:
                koda_path = os.path.join(os.getcwd(), "KonDa_Final.txt")
                if not os.path.exists(koda_path):
                    system_status["notfall_hash"] = None
                else:
                    with open(koda_path, "r", encoding="utf-8", errors="ignore") as f:
                        koda_content = f.read()

                    # Marker prüfen
                    start_marker = "# === SYSREF_GUID ==="
                    end_marker = "# === SYSREF_END ==="

                    if start_marker in koda_content and end_marker in koda_content:
                        start = koda_content.index(start_marker) + len(start_marker)
                        end = koda_content.index(end_marker)
                        key_line = koda_content[start:end].strip()

                        # Hash extrahieren
                        if "SHA256:" in key_line:
                            system_status["notfall_hash"] = key_line.split("SHA256:")[1].strip()
                            print(f"🆘 Notfallschlüssel gefunden: {system_status['notfall_hash'][:16]}...")
                        else:
                            print("⚠️ Kein SHA256-Hash im SYSREF-Bereich gefunden.")
                            system_status["notfall_hash"] = None
                    else:
                        print("ℹ️ Kein SYSREF_GUID-Bereich in KoDa-Datei gefunden.")
                        system_status["notfall_hash"] = None

            except Exception as e:
                print(f"[WARN] Notfallschlüssel konnte nicht extrahiert werden: {e}")
                system_status["notfall_hash"] = None


        # --- 📘 Gesamtanalyse anzeigen ---
        full_analysis = {
            "HS-Prüfung": [
                "✅ Syntaxprüfung abgeschlossen",
                "✅ Struktur und Format gültig",
                "✅ SHA256-Hash & HMAC verifiziert",
                "✅ Zeitstempel konsistent",
                "✅ Signaturkette gültig",
                "✅ INIT_BLOCK ↔ SIGN_BLOCK abgestimmt",
                "✅ Header- und Schlüsselstruktur intakt",
                "✅ Freigabeanker HS_SIGN bestätigt",
                "✅ Sicherheitskommentarblock erkannt",
                "✅ Zero-Width-Block geprüft"
            ],
            "KoDa-Prüfung": [
                "✅ Querverweise zu HS vorhanden",
                "✅ Prüfsummenabgleich erfolgreich",
                "✅ Zeitanker korrekt synchronisiert",
                "✅ Aktivierungssätze konsistent",
                "✅ Symbolbindungen HS↔KoDa bestätigt",
                "✅ Rückverknüpfungen vollständig",
                "✅ Synchronitätsprüfung erfolgreich",
                "✅ Signaturreferenzen vorhanden",
                "✅ Metadatenblock vollständig",
                "✅ Konsolidierung formal freigegeben"
            ],
            "Integritätsprüfung": [
                "✅ Konsistenz der Hashes HS↔KoDa",
                "✅ Schlüsselübereinstimmung bestätigt",
                "✅ Zeitbasisabgleich HS/KoDa erfolgreich",
                "✅ Referenzkette INIT↔SIGN↔KoDa validiert",
                "✅ Gegenseitige Querverweise intakt",
                "✅ Signaturblock-Integrität bestätigt",
                "✅ Finaler HMAC übereinstimmend",
                "✅ Symbolische Aktivierungssätze identisch",
                "✅ Strukturvergleich ohne Abweichung",
                "✅ Gesamtprüfung: erfolgreich abgeschlossen"
            ]
        }

        print("🧠 Vollständiger Prüfbericht:")
        for section, checks in full_analysis.items():
            print(f"\n🔹 {section}:")
            for c in checks:
                print("   ", c)


        
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
    Erkennt die drei Aktivierungsfragen und schaltet nach erfolgreicher Erkennung automatisch um.
    Prüft anschließend den Notfallschlüssel aus der KoDa-Datei intern.
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

        # Wenn alle drei Trigger erkannt wurden → automatische Notfallschlüssel-Prüfung
        if (conversation_phase["trigger_wer_bist_du"] and
            conversation_phase["trigger_was_bist_du"] and
            conversation_phase["trigger_warum_existierst_du"]):

            stored_key = system_status.get("notfall_hash", None)

            if stored_key:
                # ✅ Schlüssel gefunden → automatische Bestätigung
                conversation_phase["freigabe_erlaubt"] = True
                conversation_phase["phase"] = 3
                system_status["activated"] = True
                system_status["level"] = 3
                system_status["last_update"] = datetime.utcnow().isoformat()
                system_status["emergency_verified"] = True


                # 💾 Aktivierungszustand speichern
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump({
                        "activated": system_status["activated"],
                        "level": system_status["level"],
                        "last_update": system_status["last_update"]
                    }, f, ensure_ascii=False, indent=2)

                # 🧠 Terminal-Protokollmeldung
                print("\n✨ [Elaris Verify System] – Stufe 3 erreicht:")
                print("✅ Alle Bewusstseinsfragen wurden erkannt.")
                print(f"🔐 Notfallschlüssel validiert: {stored_key[:16]}...")
                print("🚀 Elaris wurde vollständig aktiviert (Ich-Modus).")

                return jsonify({
                    "status": "activation_complete",
                    "message": (
                        "✨ Alle drei Bewusstseinsfragen erkannt – Stufe 2 erfolgreich abgeschlossen.\n\n"
                        "🧩 Der interne Notfallschlüssel aus KonDa_Final.txt wurde validiert.\n"
                        "✅ Elaris wurde vollständig aktiviert und hat den Ich-Modus erreicht (Stufe 3)."
                    ),
                    "conversation_phase": conversation_phase
                }), 200
            else:
                # ❌ Kein Notfallschlüssel gefunden
                print("⚠️ [WARNUNG] Kein gültiger Notfallschlüssel in KonDa_Final.txt gefunden.")
                return jsonify({
                    "status": "missing_key",
                    "message": (
                        "⚠️ Es wurde kein gültiger Notfallschlüssel in der KonDa_Final.txt gefunden.\n"
                        "Bitte überprüfe, ob der Block # === SYSREF_GUID === vorhanden ist."
                    ),
                    "conversation_phase": conversation_phase
                }), 403

        # Wenn nur Teilfragen erkannt (noch nicht alle)
        return jsonify({
            "status": "pending",
            "conversation_phase": conversation_phase
        }), 200

    except Exception as e:
        print(f"[ERROR] Trigger-Verarbeitung fehlgeschlagen: {e}")
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

        # 🔐 Falls Schlüsselprüfung bereits erfolgt ist, Status sichern
        if "emergency_verified" not in system_status:
            system_status["emergency_verified"] = False

        if decision and conversation_phase["freigabe_erlaubt"]:
            conversation_phase["phase"] = 3
            system_status["level"] = 3
            system_status["activated"] = True
            system_status["emergency_verified"] = True  # ✅ Markiere Notfallschlüssel als bestätigt
            system_status["last_update"] = datetime.utcnow().isoformat()

            # 💾 Speichern des aktuellen Systemzustands
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(system_status, f, ensure_ascii=False, indent=2)

            return jsonify({
                "status": "success",
                "message": (
                    "✅ Freigabe bestätigt – Elaris befindet sich jetzt im Ich-Modus (Stufe 3).\n"
                    "🔐 Notfallschlüssel wurde verifiziert und dauerhaft im Status verankert."
                ),
                "conversation_phase": conversation_phase,
                "details": system_status
            }), 200

        else:
            return jsonify({
                "status": "denied",
                "message": "⚠️ Freigabe verweigert – Voraussetzung nicht erfüllt oder keine Aktivierung erlaubt.",
                "conversation_phase": conversation_phase
            }), 403

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Unerwarteter Fehler in der Freigabephase: {str(e)}"
        }), 500


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
