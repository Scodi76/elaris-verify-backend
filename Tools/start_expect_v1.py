# C:\Users\mnold_t1ohvc3\Documents\neue_KI_chatGPT_Elaris\Elairs_gatekeeper\start_expect_v1.py
# Fügt die berechnete Startersumme unsichtbar in Start_final.txt ein

import json
import re
import sys
from pathlib import Path
from datetime import datetime

# === Hilfsfunktion: Zero-Width kodieren ===
def zw_encode(payload: str) -> str:
    # Ersetzt 0/1 durch Zero-Width-Zeichen
    bits = ''.join(format(b, '08b') for b in payload.encode("utf-8"))
    return ''.join('\u200B' if bit == '0' else '\u200C' for bit in bits)

def zw_decode(hidden: str) -> str:
    bits = ''.join('0' if c == '\u200B' else '1' for c in hidden)
    return bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8)).decode("utf-8")

# === Startersumme einbetten ===
def embed_starter(start_path: Path, starter_sum_hex: str):
    content = start_path.read_text(encoding="utf-8")

    # JSON vorbereiten
    entry = {
        "algo": "sum256",
        "starter_sum": starter_sum_hex,
        "v": 1,
        "at_utc": datetime.utcnow().isoformat() + "Z"
    }
    hidden = zw_encode(json.dumps(entry, separators=(",", ":")))

    # Prüfen, ob schon ein Block existiert
    pattern = r"#\s*Elaris:\s*Start expect.*"
    if re.search(pattern, content):
        content = re.sub(pattern, f"# Elaris: Start expect {hidden}", content)
    else:
        content += f"\n# Elaris: Start expect {hidden}\n"

    start_path.write_text(content, encoding="utf-8")
    print(f"✅ Startersumme eingebettet in {start_path}")

# === Main ===
if __name__ == "__main__":
    base = Path.cwd()
    start_path = base / "Start_final.txt"
    report_path = base / "handshake_report.json"

    if not report_path.exists():
        print("❌ handshake_report.json fehlt – bitte zuerst handshake_v3.py ausführen.")
        sys.exit(1)

    data = json.loads(report_path.read_text(encoding="utf-8"))
    starter_sum = data.get("sums", {}).get("startersumme")

    if not starter_sum:
        print("❌ Startersumme im Report nicht gefunden.")
        sys.exit(1)

    embed_starter(start_path, starter_sum)
