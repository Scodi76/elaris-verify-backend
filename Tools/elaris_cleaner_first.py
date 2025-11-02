# 🧹 Elaris First-File Cleaner – Version 1.0
# Pfad: C:\Elaris_KI_Versions\Elairs_gatekeeper\tools\elaris_cleaner_first.py
# Zweck: Reinigung der *_first.txt-Dateien (HS, KonDa, Start)
# Optionen:
#   --overwrite   → ersetzt Originaldateien nach Backup
#   --silent      → unterdrückt Konsolenausgabe (nur Log)

import os, re, sys, json, hashlib
from datetime import datetime
from pathlib import Path

# === BASISPFAD ===
BASE = Path(__file__).parent
CONFIG_FILE = BASE / "clean_first_config.json"

# === KONFIG LADEN ===
if CONFIG_FILE.exists():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        CONFIG = json.load(f)
else:
    print("❌ Keine Konfiguration gefunden.")
    sys.exit(1)

LOG_FILE = BASE / CONFIG.get("log_file", "clean_first_log.txt")
BACKUP_DIR = BASE / CONFIG.get("backup_dir", "backups")
FILES = CONFIG.get("files", [])
REMOVE_PATTERNS = CONFIG.get("remove_patterns", [])
ZERO_WIDTH = CONFIG.get("zero_width_chars", [])

os.makedirs(BACKUP_DIR, exist_ok=True)

# === PARAMETER ===
OVERWRITE = "--overwrite" in sys.argv
SILENT = "--silent" in sys.argv

def log(msg):
    """Schreibt Log-Einträge sowohl in Datei als auch optional in Konsole."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    with open(LOG_FILE, "a", encoding="utf-8") as lf:
        lf.write(line + "\n")
    if not SILENT:
        print(line)

def hash_file(path: Path):
    """Berechnet SHA-256-Hash einer Datei."""
    try:
        data = path.read_bytes()
        return hashlib.sha256(data).hexdigest()
    except Exception:
        return None

def clean_content(text: str) -> str:
    """Entfernt Zero-Width-Zeichen, Meta-Blöcke und doppelte Leerzeilen."""
    for zw in ZERO_WIDTH:
        text = text.replace(zw, "")
    for pattern in REMOVE_PATTERNS:
        text = re.sub(rf"{pattern}.*?(?:\n|$)", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"\n\s*\n+", "\n\n", text.strip()) + "\n"
    return text

def process_file(fname: str):
    fpath = BASE / fname
    if not fpath.exists():
        log(f"⚠️ Datei fehlt: {fname}")
        return

    log(f"📄 Bearbeite: {fname}")
    try:
        original = fpath.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        log(f"❌ Fehler beim Lesen von {fname}: {e}")
        return

    original_hash = hash_file(fpath)
    cleaned = clean_content(original)
    cleaned_hash = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()

    # Vergleich & Speicherung
    if original_hash == cleaned_hash:
        log(f"🟢 {fname}: Keine Änderungen erforderlich (bereits sauber).")
        return

    cleaned_file = fpath.with_name(f"{fpath.stem}_cleaned.txt")
    cleaned_file.write_text(cleaned, encoding="utf-8")
    log(f"✅ Bereinigt gespeichert: {cleaned_file.name}")

    if OVERWRITE:
        backup_file = BACKUP_DIR / f"{fpath.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            # Backup anlegen
            fpath.replace(backup_file)
            log(f"📦 Backup erstellt: {backup_file.name}")

            # Bereinigte Version als Original zurückschreiben
            cleaned_file.replace(fpath)
            log(f"⚙️ Original ersetzt: {fname}")
        except Exception as e:
            log(f"❌ Fehler beim Überschreiben: {e}")

    # Hashvergleich ins Log
    log(f"🔍 Hash-Vergleich {fname}:")
    log(f"   Vorher : {original_hash[:16]}...")
    log(f"   Nachher: {cleaned_hash[:16]}...")
    log("-" * 60)

def main():
    header = f"\n{'='*60}\n🧹 Elaris First-File Cleaner – {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}"
    with open(LOG_FILE, "a", encoding="utf-8") as lf:
        lf.write(header + "\n")

    for file in FILES:
        process_file(file)

    log("✅ Vorgang abgeschlossen.")
    log("=" * 60)

if __name__ == "__main__":
    main()
