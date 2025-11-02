# 🔄 sync_meta_blocks.py – UTF-safe Version v1.1
# Synchronisiert sichtbare Metablocks (UTF-kompatibel)

from pathlib import Path
import hashlib
import json
import sys

USE_ASCII = False
try:
    "🧩".encode(sys.stdout.encoding or "utf-8")
except Exception:
    USE_ASCII = True

def icon(emoji, fallback):
    return fallback if USE_ASCII else emoji

BASE = Path.cwd()

def compute_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def ensure_visible_meta(path: Path, new_hash: str) -> bool:
    text = path.read_text(encoding="utf-8")
    updated = False

    if "#⟐HS-META-BEGIN" in text:
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if '"sha256":' in line:
                old_hash = line.split(":")[1].strip().strip('" ,')
                lines[i] = f'  "sha256": "{new_hash}",'
                updated = True
                print(f"     alt: {old_hash[:12]}... -> neu: {new_hash[:12]}...")
        path.write_text("\n".join(lines), encoding="utf-8")

    return updated

def main():
    print(f"{icon('🧩','[SYNC]')} Starte Metadaten-Synchronisation...")

    for f in ["HS_Final.txt", "KonDa_Final.txt"]:
        file_path = BASE / f
        if not file_path.exists():
            print(f"{icon('⚠️','[WARN]')} Datei fehlt: {f}")
            continue
        new_hash = compute_sha256(file_path)
        print(f"{icon('🔹','[HASH]')} {f}: SHA256 aktualisiert.")
        ensure_visible_meta(file_path, new_hash)

    print(f"{icon('✅','[OK]')} Metablocks erfolgreich synchronisiert.")

if __name__ == "__main__":
    main()
