# 🔐 Elaris Handshake v4 – Unicode-sichere Variante (Windows-kompatibel)
import json, re, hashlib, sys
from pathlib import Path
from datetime import datetime

def safe_print(*args, **kwargs):
    """Druckt Unicode-sicher unter Windows (ersetzt Emojis)."""
    text = " ".join(str(a) for a in args)
    replacements = {
        "✅": "[OK]",
        "❌": "[ERR]",
        "⚠️": "[WARN]",
        "🔢": "[SUMME]",
        "🔍": "[CHECK]"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    print(text, **kwargs)

def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def strip_zero_chars(text: str) -> str:
    return re.sub(r"[\u200B-\u200F\u2060\uFEFF]", "", text)

def extract_block(content: str) -> str:
    m = re.search(r"[\u200B\u200C\u200D\u2060]+", content)
    if m: return m.group(0)
    m = re.search(r"[01]{64,}", content)
    return m.group(0) if m else ""

def decode_block(content: str):
    zw_raw = extract_block(content)
    if not zw_raw: return None
    bits = "".join("0" if c == "\u200b" else "1" if c == "\u200c" else "" for c in zw_raw)
    bits = bits.ljust((len(bits)+7)//8*8, "0")
    try:
        data = bytes(int(bits[i:i+8], 2) for i in range(0,len(bits),8))
        return json.loads(data.decode("utf-8", "ignore"))
    except: return None

def sha256_hex(data: str): return hashlib.sha256(data.encode()).hexdigest()

def verify_meta(path: Path):
    content = read_file(path)
    meta = decode_block(content)
    if not meta: return None, "[ERR] Kein Metablock"
    calc = sha256_hex(strip_zero_chars(content))
    if meta.get("sha256") != calc: return meta, "[WARN] SHA256 stimmt nicht"
    return meta, "[OK]"

def handshake(hs_path, koda_path, out_path):
    rep = {"timestamp": datetime.utcnow().isoformat()+"Z", "status":"initial","details":{}}
    hs_meta, hs_stat = verify_meta(hs_path)
    koda_meta, koda_stat = verify_meta(koda_path)
    rep["details"]["HS_Final"] = hs_stat
    rep["details"]["KoDa_Final"] = koda_stat

    if not hs_meta or not koda_meta:
        rep["status"] = "failed"
        out_path.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
        safe_print("❌ Handshake fehlgeschlagen – Metadaten fehlen.")
        return

    safe_print("\n✅ Handshake erfolgreich abgeschlossen.")
    hs_sum = int(hs_meta["sha256"], 16)
    koda_sum = int(koda_meta.get("sha256") or koda_meta.get("digest"), 16)
    starter_sum = (hs_sum + koda_sum) % (2**256)
    rep["status"] = "success"
    rep["sums"] = {"starter_sum_hex": hex(starter_sum)}
    out_path.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    safe_print("🔢 Starter-Summe:", hex(starter_sum))

if __name__ == "__main__":
    base = Path.cwd()
    handshake(base/"HS_Final.txt", base/"KonDa_Final.txt", base/"handshake_report.json")
