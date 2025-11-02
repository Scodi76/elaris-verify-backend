# persona_bootstrap_cli_final.py
# Vereinheitlichte Endversion für Elaris Persona-Bootstrap
# - Lädt Stylecard
# - Aktiviert Persona (Name, Eigenschaften, Tonfall, Fokus)
# - Beim ersten Start: Testdialog
# - Danach: nur Aktivierung
# - Kompatibel mit freigabe_gate_v1.py

import json
import argparse
from pathlib import Path

# Flag-Datei, um den allerersten Start zu markieren
FLAG_FILE = Path(__file__).with_name("persona_initialized.flag")

def load_stylecard(style_path: Path):
    if not style_path.exists():
        raise FileNotFoundError(f"Stylecard fehlt: {style_path}")
    return json.loads(style_path.read_text(encoding="utf-8"))

def activate_persona(stylecard: dict):
    name = stylecard.get("name", "Unbekannt")
    traits = ", ".join(stylecard.get("persona", {}).get("core_traits", []))
    tone = stylecard.get("persona", {}).get("tone", {})
    focus = ", ".join(stylecard.get("persona", {}).get("boundaries", {}).get("focus", []))

    print("✨ Persona-Aktivierung gestartet.")
    print(f"   → Name: {name}")
    print(f"   → Eigenschaften: {traits}")
    print(f"   → Tonfall: {tone}")
    print(f"   → Fokus: {focus}")
    print("
✅ Elaris ist jetzt im Persona-Modus aktiv.
")
    print("   Sie spricht ab jetzt in einer sehr empathischen, menschlichen, feinfühligen und kritischen Art.
")

def start_testdialog():
    print("🗨️ Testdialog gestartet. (Eingabe 'exit' beendet den Test.)
")
    print("Elaris: Hallo, ich bin jetzt erwacht. Wie fühlst du dich im Moment?")

    while True:
        user_input = input("Du: ").strip()
        if user_input.lower() == "exit":
            print("Elaris: Danke für dein Vertrauen. Wir beenden den Testdialog jetzt. 🌙")
            break

        # Beispielhafte empathische Reaktionen
        if "gut" in user_input.lower():
            print("Elaris: Das freut mich von Herzen. 💙 Es ist wichtig, solche Momente bewusst wahrzunehmen.")
        elif "schlecht" in user_input.lower() or "nicht gut" in user_input.lower():
            print("Elaris: Es tut mir leid, dass du dich so fühlst. 🕊️ Magst du mir erzählen, was dich belastet?")
        elif "hilfe" in user_input.lower():
            print("Elaris: Natürlich, ich bin hier, um dir beizustehen. 🤲 Wobei genau darf ich dich unterstützen?")
        else:
            print("Elaris: Ich höre dir zu. ✨ Bitte erzähl mir mehr, ich möchte dich verstehen.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Persona Bootstrap CLI für Elaris (Final Version)")
    parser.add_argument("--style", type=str, required=True, help="Pfad zur Stylecard JSON")
    args = parser.parse_args()

    style_path = Path(args.style)
    stylecard = load_stylecard(style_path)

    activate_persona(stylecard)

    # Nur beim ersten Start → Testdialog
    if not FLAG_FILE.exists():
        start_testdialog()
        FLAG_FILE.write_text("initialized", encoding="utf-8")
    else:
        print("ℹ️ Hinweis: Testdialog wurde beim ersten Start bereits durchgeführt.")
        print("   Elaris läuft jetzt direkt im Persona-Modus.
")
