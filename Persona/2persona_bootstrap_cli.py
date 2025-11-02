# persona_bootstrap_cli.py
# Startet die Persona-Aktivierung für Elaris basierend auf einer Stylecard

import json
import argparse
from pathlib import Path

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
    print("\n✅ Elaris ist jetzt im Persona-Modus aktiv.")
    print("   Sie spricht ab jetzt in einer sehr empathischen, menschlichen, feinfühligen und kritischen Art.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Persona Bootstrap CLI für Elaris")
    parser.add_argument("--style", type=str, required=True, help="Pfad zur Stylecard JSON")
    args = parser.parse_args()

    style_path = Path(args.style)
    stylecard = load_stylecard(style_path)
    activate_persona(stylecard)
