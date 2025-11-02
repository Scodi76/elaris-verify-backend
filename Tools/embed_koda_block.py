# 🔐 embed_koda_block.py – UTF-safe Version v1.2
# Fügt Zero-Width-Metablock in KonDa_Final.txt ein
# Keine Unicode-Pfeile oder Emojis

from pathlib import Path
import hashlib
import json
import shutil
import sys

USE_ASCII = False
try:
    "→".encode(sys.stdout.encoding or "utf-8")
except Exception:
    USE_ASCII = True

def arrow():
    return "->" if USE_ASCII else "→"

def encode_zero_width(text: str) -> str:
    mapping = {'0': '\u200b', '1': '\u200c'}
    binary = ''.join(f"{ord(c):08b}" for c in text)
    return ''.join(mapping[b] for b in binary)

def main():
    src = Path("KonDa_Final.txt")
    if not src.exists():
        print("[ERROR] KonDa_Final.txt nicht gefunden!")
        return

    backup = Path("KonDa_Final_first.txt")
    print(f"[INFO] Backup: KonDa_Final.txt {arrow()} {backup.name}")
    shutil.copy2(src, backup)

    content = src.read_text(encoding="utf-8")
    sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    meta = {"v": "1.2", "sha256": sha256, "type": "koda-meta"}

    zw_block = encode_zero_width(json.dumps(meta, separators=(',', ':')))
    result = content.rstrip() + "\n\n#KODA-ZW-BEGIN\n" + zw_block + "\n#KODA-ZW-END\n"

    src.write_text(result, encoding="utf-8")

    print("[OK] Zero-Width-Metablock in KonDa_Final.txt eingebettet.")
    print(f"[DEBUG] Block-Länge: {len(zw_block)}")
    print("[DEBUG] Erste 80 sichtbare Bits:",
          zw_block[:80].replace('\u200b', '0').replace('\u200c', '1'))

if __name__ == "__main__":
    main()
