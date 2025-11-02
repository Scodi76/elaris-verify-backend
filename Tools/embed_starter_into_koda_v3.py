# 🔐 embed_starter_into_koda_v3.8 – UTF-safe & Auto-Repair-ready
# Zero-Width + Sichtbarer Fallback-Metablock + Sicherer Backup-Prozess
# Kompatibel mit Windows-Terminal (CP1252)
# Keine Emojis, keine Sonderzeichen → stabil für Auto-Gatekeeper

from pathlib import Path
import hashlib
import json
import string
import shutil
import sys

# ===========================================================
# 🔹 Terminal-Kompatibilität
# ===========================================================

USE_ASCII = False
try:
    "→".encode(sys.stdout.encoding or "utf-8")
except Exception:
    USE_ASCII = True

def arrow():
    return "->" if USE_ASCII else "→"

# ===========================================================
# 🔹 Hilfsfunktionen
# ===========================================================

def extract_stylometrics(text: str) -> dict:
    """Extrahiert einfache Textmetriken zur Signaturerkennung."""
    lines = text.splitlines()
    return {
        "char_count": sum(len(line) for line in lines),
        "i_points": text.count("i"),
        "whitespace_count": text.count(" "),
        "line_count": len(lines),
        "comment_line_count": sum(1 for line in lines if line.strip().startswith("#")),
        "punctuation_count": sum(1 for c in text if c in string.punctuation)
    }

def encode_zero_width(data_str: str) -> str:
    """Kodiert JSON-String in Zero-Width-Bits."""
    mapping = {'0': '\u200b', '1': '\u200c'}
    binary = ''.join(f"{ord(c):08b}" for c in data_str)
    return ''.join(mapping[b] for b in binary)

# ===========================================================
# 🔸 Hauptfunktion
# ===========================================================

def embed_koda_block(source_file: str, output_file: str):
    """
    Fügt Zero-Width + sichtbaren Fallback-Metablock in KonDa_Final.txt ein.
    Erstellt automatisch Backup und schreibt Ergebnis in Ausgabe.
    """
    src = Path(source_file)
    if not src.exists():
        raise FileNotFoundError("KonDa_Final.txt wurde nicht gefunden!")

    text = src.read_text(encoding="utf-8", errors="ignore")

    # ===========================================================
    # 🧩 Cross-Link zur HS automatisch einfügen
    # ===========================================================
    crosslink_header = (
        "# =========================================\n"
        "# Cross-Link-Reference: HS_Final_embedded_v3\n"
        "# Hinweis:\n"
        "# Diese KoDa-Version ist mit der Hauptsignatur HS_Final_embedded_v3 verknüpft.\n"
        "# Der Cross-Link dient der Integritätsprüfung zwischen HS und KoDa.\n"
        "# =========================================\n\n"
        "# 🧠 Emotionale Trigger-Kompatibilität\n"
        "# Diese HS-Version unterstützt emotionale Resonanz-Antworten für Triggerfragen.\n"
        "# Verknüpfte Triggerabfolge (EVS/ELARIS):\n"
        "# 1️⃣ wer bist du\n"
        "# 2️⃣ was bist du\n"
        "# 3️⃣ warum existierst du\n"
        "# 4️⃣ wie siehst du deine beziehung mit mir\n"
        "#\n"
        "# Nach dem dritten Trigger erfolgt die emotionale Übergabe\n"
        "# an Elaris (Ich-Modus), die Antwort wird dynamisch erzeugt\n"
        "# und basiert auf moralisch-symbolischer Tiefenanalyse.\n"
        "#\n"
        "# ⚠️ Wichtig:\n"
        "# Diese Triggerfolge darf nur in kontrollierter Umgebung\n"
        "# (EVS-Freigabe) verwendet werden.\n"
        "# Die Antworten sind semantisch generativ (nicht statisch).\n"
        "#\n"
        "# Integration: verified emotional layer – GPT-basiert\n"
        "# Evaluationsphase: automatisch in Verify-Backend aktiv.\n"
        "# =========================================\n\n"
        )

    

    # Nur hinzufügen, wenn er noch nicht existiert
    if "Cross-Link-Reference: HS_Final_embedded_v3" not in text:
        text = crosslink_header + text
        print("[INFO] Cross-Link-Header hinzugefügt (HS_Final_embedded_v3).")
    else:
        print("[INFO] Cross-Link-Header bereits vorhanden – übersprungen.")

    # ===========================================================
    # 📊 Stylometrie + Hash
    # ===========================================================
    metrics = extract_stylometrics(text)
    sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()

    build_meta = {
        "v": "3.8",
        "type": "build-meta",
        "file": "KonDa_Final.txt",
        "sha256": sha256,
        "metrics": metrics
    }

    # Zero-Width-Block
    zw_block = encode_zero_width(json.dumps(build_meta, separators=(",", ":")))

    # Sichtbarer Block
    visible_meta = (
        "#KODA-META-BEGIN\n"
        + json.dumps(build_meta, indent=2, ensure_ascii=False)
        + "\n#KODA-META-END\n"
    )

    # Zusammenführen
    result = (
        text.rstrip()
        + "\n\n#KODA-ZW-BEGIN\n"
        + zw_block
        + "\n#KODA-ZW-END\n"
        + visible_meta
        + "\n"
    )

    # ===========================================================
    # 🧠 Debug-Ausgabe
    # ===========================================================
    print("[DEBUG] Zero-Width-Block-Länge:", len(zw_block))
    print("[DEBUG] Erste 80 sichtbare Bits:",
          zw_block[:80].replace("\u200b", "0").replace("\u200c", "1"))

    # ===========================================================
    # 💾 Backup speichern
    # ===========================================================
    original_path = Path("KonDa_Final.txt")
    backup_path = Path("KonDa_Final_first.txt")

    if original_path.exists():
        print(f"[INFO] Backup: KonDa_Final.txt {arrow()} KonDa_Final_first.txt")
        try:
            shutil.copy2(original_path, backup_path)
            print("[OK] Backup erfolgreich erstellt:", backup_path.name)
        except Exception as e:
            print("[WARN] Backup fehlgeschlagen:", e)

    # ===========================================================
    # 📝 Schreiben
    # ===========================================================
    try:
        Path("KonDa_Final.txt").write_text(result, encoding="utf-8")
        Path(output_file).write_text(result, encoding="utf-8")
        print("[OK] Cross-Link + Zero-Width + Fallback-Metablock eingebettet.")
    except Exception as e:
        print("[ERROR] Fehler beim Schreiben:", e)
        raise

# ===========================================================
# 🧠 MAIN ENTRY
# ===========================================================

if __name__ == "__main__":
    SOURCE = "KonDa_Final.txt"
    OUTPUT = "KonDa_Final_embedded_v3.py"

    if not Path(SOURCE).exists():
        raise FileNotFoundError(f"{SOURCE} fehlt!")

    print(f"[INFO] Backup: KonDa_Final.txt {arrow()} KonDa_Final_first.txt")
    shutil.copy2(SOURCE, "KonDa_Final_first.txt")

    embed_koda_block(SOURCE, OUTPUT)

    print("[OK] Einbettung abgeschlossen. Datei ist bereit für Handshake.")
