# C:\Users\mnold_t1ohvc3\Documents\neue_KI_chatGPT_Elaris\Elairs_gatekeeper\run_gatekeeper_full.py
# 🔐 Elaris Gatekeeper Full AutoRun v1.2
# Enthält Fix für derive_keys (keys_out.json-Erstellung)

import subprocess
import json
from datetime import datetime
from pathlib import Path

BASE = Path.cwd()

FILES = {
    "ram_proof": BASE / "RAM_PROOF.json",
    "hs_final": BASE / "HS_Final.txt",
    "koda_final": BASE / "KonDa_Final.txt",
    "keys": BASE / "keys_out.json",
    "baseline": BASE / "integrity_baseline.json",
    "report": BASE / "process_report.json"
}

SCRIPTS = {
    "ram_proof": "generate_ram_proof.py",
    "hs_embed": "embed_starter_into_hs_v3.py",
    "repair": "embed_starter_into_hs_v3.py",
    "koda_embed": "embed_koda_block.py",
    "sync_meta": "sync_meta_blocks.py",
    "verify": "verify_integrity.py",
    "baseline": "integrity_snapshot.py",
    "derive_keys": "derive_keys_v1.py"  # 🔹 hinzugefügt
}

REPORT = {
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "steps": [],
    "status": "initial"
}

def run_script(name, args=None):
    script_path = SCRIPTS.get(name)
    if not script_path:
        return {"step": name, "status": "skipped", "output": "Kein Skript definiert."}
    
    full_path = BASE / script_path
    if not full_path.exists():
        return {"step": name, "status": "error", "output": f"{script_path} fehlt!"}
    
    cmd = ["python", str(full_path)]
    if args:
        cmd += args
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    out = (result.stdout or "") + (result.stderr or "")
    status = "ok" if result.returncode == 0 else "warn"
    return {"step": name, "status": status, "output": out.strip()[:4000]}

def append_step(name, result):
    REPORT["steps"].append({
        "name": name,
        "status": result.get("status"),
        "snippet": result.get("output", "").splitlines()[:8]
    })

# ====================================================
# 1️⃣ RAM Proof
# ====================================================
if not FILES["ram_proof"].exists():
    res = run_script("ram_proof")
    append_step("RAM Proof (Erzeugung)", res)
else:
    append_step("RAM Proof (Übersprungen)", {"status": "ok", "output": "Bereits vorhanden."})

# ====================================================
# 2️⃣ HS Embed + Handshake
# ====================================================
res_hs = run_script("hs_embed")
append_step("HS Embed / Handshake", res_hs)

if "Integritätsprüfung fehlgeschlagen" in res_hs["output"] or res_hs["status"] != "ok":
    print("Reparaturmodus wird aktiviert...")
    repair_res = run_script("repair", ["--no-handshake"])
    append_step("[REPAIR] Repair Kit (Auto)", repair_res)
else:
    append_step("[REPAIR] Repair Kit (Auto)", {"status": "ok", "output": "Kein Reparaturlauf erforderlich."})

# ====================================================
# 3️⃣ KoDa Embed
# ====================================================
if FILES["koda_final"].exists():
    res = run_script("koda_embed")
    append_step("KoDa Embed", res)
else:
    append_step("KoDa Embed", {"status": "warn", "output": "KonDa_Final.txt fehlt!"})

# ====================================================
# 4️⃣ Synchronisierung
# ====================================================
res = run_script("sync_meta")
append_step("Meta Sync", res)

# ====================================================
# 5️⃣ Schlüsselableitung (NEU)
# ====================================================
if not FILES["keys"].exists():
    res = run_script("derive_keys")
    append_step("Keys Ableitung", res)
else:
    append_step("Keys Ableitung", {"status": "ok", "output": "keys_out.json bereits vorhanden."})

# ====================================================
# 6️⃣ Integritätsprüfung
# ====================================================
res = run_script("verify")
append_step("Integritätsprüfung", res)

# ====================================================
# 7️⃣ Baseline Snapshot
# ====================================================
if not FILES["baseline"].exists():
    res = run_script("baseline")
    append_step("Baseline Snapshot", res)
else:
    append_step("Baseline Snapshot", {"status": "ok", "output": "Bereits vorhanden."})

# ====================================================
# 8️⃣ Abschlussbewertung
# ====================================================
statuses = [s["status"] for s in REPORT["steps"]]
if "error" in statuses:
    REPORT["status"] = "❌ Fehler"
elif "warn" in statuses:
    REPORT["status"] = "⚠️ Warnung"
else:
    REPORT["status"] = "✅ Erfolgreich"

REPORT["finished"] = datetime.utcnow().isoformat() + "Z"

# ====================================================
# 9️⃣ Ergebnis speichern
# ====================================================
FILES["report"].write_text(json.dumps(REPORT, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\n📄 Report gespeichert in: {FILES['report']}")
print(f"🔎 Gesamtstatus: {REPORT['status']}")

# ====================================================
# 🔟 GUI anzeigen
# ====================================================
GUI_SCRIPT = BASE / "lock_console_gui.py"
if GUI_SCRIPT.exists():
    subprocess.Popen(["python", str(GUI_SCRIPT)], shell=True)
else:
    print("⚠️ GUI (lock_console_gui.py) nicht gefunden – bitte manuell starten.")
