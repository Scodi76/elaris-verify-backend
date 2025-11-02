from pathlib import Path
import re

def remove_zero_width_and_hidden_blocks(text: str) -> str:
    # Entferne alle Zero-Width-Zeichen (unsichtbare Unicode)
    text = re.sub(r'[\u200b\u200c\u200d\u200e\u200f]', '', text)

    # Entferne mögliche Elaris-Build-Meta- oder Hidden-Blocks
    text = re.sub(r'# Elaris: HS build-meta.*?(?=\n#|\Z)', '', text, flags=re.DOTALL)
    text = re.sub(r'#⟐HS-ZW:.*', '', text)
    text = re.sub(r'#⟐ELARIS-KEY-ZW:.*', '', text)
    text = re.sub(r'# Elaris: KoDa.*?(?=\n#|\Z)', '', text, flags=re.DOTALL)

    # Leere Zeilen mehrfach entfernen
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

# Hauptprozess
source = Path("HS_Final.txt")
cleaned = Path("HS_Final_clean.txt")

if not source.exists():
    raise FileNotFoundError("HS_Final.txt wurde nicht gefunden.")

content = source.read_text(encoding="utf-8")
cleaned_content = remove_zero_width_and_hidden_blocks(content)
cleaned.write_text(cleaned_content, encoding="utf-8")

print("[✔] HS_Final.txt wurde gereinigt.")
print("[→] Gespeichert als:", cleaned.name)
