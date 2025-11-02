import json
import hashlib
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
OUT_FILE = BASE / "integrity_baseline.json"

def hash_file(path: Path) -> str:
    """Berechnet SHA256-Hash für eine Datei."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def main():
    print("[SNAP] Erstelle Integritäts-Baseline...")

    files = [
        "HS_Final.txt",
        "KonDa_Final.txt",
        "Start_final.txt",
    ]

    baseline = {
        "timestamp": datetime.utcnow().isoformat(),
        "files": {}
    }

    for file in files:
        path = BASE / file
        if path.exists():
            baseline["files"][file] = hash_file(path)
            print(f"[OK] {file}: {baseline['files'][file][:12]}...")
        else:
            print(f"[WARN] Datei fehlt: {file}")

    # Speichern
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)

    # ✅ Fehlerquelle korrigiert – jetzt korrekt formatiert
    print(f"[OK] Integritäts-Baseline gespeichert: {OUT_FILE.name}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[EXCEPTION] {e}")
