from pathlib import Path

def clean_zero_block(input_path, output_path=None):
    zero_width_chars = [
        '\u200b',  # Zero Width Space
        '\u200c',  # Zero Width Non-Joiner
        '\u200d',  # Zero Width Joiner
        '\u200e',  # Left-to-Right Mark
        '\u200f',  # Right-to-Left Mark
        '\u2060'   # Word Joiner
    ]

    path = Path(input_path)
    text = path.read_text(encoding="utf-8")

    # Alle Zero-Width-Zeichen löschen
    for zw in zero_width_chars:
        text = text.replace(zw, "")

    # Zeilen mit eingebettetem Kommentar entfernen
    lines = text.splitlines()
    cleaned_lines = [
        line for line in lines
        if not line.strip().startswith("#⟐HS-ZW:")
        and not line.strip().startswith("# Elaris: HS build-meta")
    ]
    cleaned_text = "\n".join(cleaned_lines)

    # Ergebnis speichern
    if output_path:
        Path(output_path).write_text(cleaned_text, encoding="utf-8")
        print(f"[OK] Gereinigte Kopie gespeichert als: {output_path}")
    else:
        path.write_text(cleaned_text, encoding="utf-8")
        print(f"[OK] Datei direkt bereinigt: {input_path}")

if __name__ == "__main__":
    source = "HS_Final_first.txt"
    target = "HS_Final_first_clean.txt"  # sichere Kopie

    clean_zero_block(source, target)
