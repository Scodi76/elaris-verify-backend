# 🔐 lock_console_gui.py
# GUI-Konsole für Baseline-Verwaltung (Status / Reset / Unlock / Verify)
# Version: 1.3 – Automatische Nachprüfung + Topmost-Funktion
# Sicherheitsstufe: Level 5 (autorisiert, manipulationssicher)

import json
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, scrolledtext
from datetime import datetime

BASE = Path.cwd()
LOCK_PATH = BASE / "baseline.lock"
BASELINE_PATH = BASE / "integrity_baseline.json"
RESET_SCRIPT = BASE / "reset_baseline_secure.py"
VERIFY_SCRIPT = BASE / "verify_integrity.py"

# =============================================
# 🔹 Hilfsfunktionen
# =============================================

def read_json_safe(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def show_status(textbox, header_label=None):
    textbox.delete("1.0", tk.END)
    textbox.insert(tk.END, "🔍 Prüfe aktuellen Baseline-Lock...\n\n")

    # Lock prüfen
    if not LOCK_PATH.exists():
        textbox.insert(tk.END, "✅ Kein Lock aktiv – Baseline frei.\n\n")
        if header_label:
            header_label.config(text="✅ Baseline frei – Änderungen erlaubt", fg="#00ff66")
    else:
        data = read_json_safe(LOCK_PATH)
        if not data:
            textbox.insert(tk.END, "⚠️ Lock-Datei beschädigt oder leer.\n")
            if header_label:
                header_label.config(text="⚠️ Lock-Datei beschädigt!", fg="#ff6600")
        else:
            textbox.insert(tk.END, f"🔒 Lock aktiv seit: {data.get('created','?')}\n")
            textbox.insert(tk.END, f"👤 Autorisiert durch: {data.get('authorized_by','?')}\n")
            textbox.insert(tk.END, f"🔑 Hash: {data.get('hash_used','?')[:16]}...\n\n")
            if header_label:
                header_label.config(text="🔒 System gesperrt – autorisierte Freigabe erforderlich", fg="#ff4444")

    # Baseline prüfen
    if BASELINE_PATH.exists():
        base = read_json_safe(BASELINE_PATH)
        if base:
            ts = base.get("timestamp", "?")
            hs = base.get("trusted_hashes", {}).get("HS_Final", "?")[:12]
            kd = base.get("trusted_hashes", {}).get("KoDa_Final", "?")[:12]
            textbox.insert(tk.END, f"📘 Baseline-Zeit: {ts}\n")
            textbox.insert(tk.END, f"🔹 HS_Final: {hs}...\n")
            textbox.insert(tk.END, f"🔹 KoDa_Final: {kd}...\n")
        else:
            textbox.insert(tk.END, "⚠️ Fehler beim Lesen der Baseline.\n")
    else:
        textbox.insert(tk.END, "⚠️ Keine Baseline gefunden.\n")

    textbox.insert(tk.END, "\n✅ Statusprüfung abgeschlossen.\n")

def run_reset_secure():
    confirm = messagebox.askyesno("Bestätigung", "Willst du den autorisierten Reset starten?")
    if not confirm:
        return
    subprocess.run(["python", str(RESET_SCRIPT)], shell=True)

def verify_integrity_report(textbox):
    textbox.delete("1.0", tk.END)
    textbox.insert(tk.END, "🔍 Integritätsprüfung läuft...\n\n")
    try:
        result = subprocess.run(["python", str(VERIFY_SCRIPT)], capture_output=True, text=True, shell=True)
        textbox.insert(tk.END, result.stdout)
        textbox.insert(tk.END, "\n✅ Prüfung abgeschlossen.\n")
    except Exception as e:
        textbox.insert(tk.END, f"❌ Fehler bei Prüfung: {e}\n")

def run_unlock_force(textbox, header_label):
    """Lock löschen → sofort Nachprüfung"""
    if not LOCK_PATH.exists():
        messagebox.showinfo("Info", "Kein Lock vorhanden.")
        return

    confirm = messagebox.askyesno(
        "Sicherheitsabfrage",
        "⚠️ Lock-Datei wirklich löschen?\nNur verwenden, wenn der autorisierte Zugang verloren ist."
    )
    if not confirm:
        return

    try:
        LOCK_PATH.unlink()
        messagebox.showinfo("Erfolg", "Lock-Datei wurde entfernt.")
        show_status(textbox, header_label)
        textbox.insert(tk.END, "\n🧩 Lock entfernt – starte automatische Nachprüfung...\n\n")
        verify_integrity_report(textbox)
    except Exception as e:
        messagebox.showerror("Fehler", f"Lock konnte nicht entfernt werden:\n{e}")

# =============================================
# 🧠 GUI
# =============================================

def open_console():
    root = tk.Tk()
    root.title("🧠 Elaris Baseline-Konsole")
    root.geometry("780x600")
    root.configure(bg="#111")

    # 🔝 Immer im Vordergrund
    root.attributes("-topmost", True)

    header_label = tk.Label(
        root, text="🔍 Baseline wird geprüft...",
        bg="#111", fg="#cccccc", font=("Consolas", 13, "bold")
    )
    header_label.pack(pady=10)

    tk.Label(
        root, text="🧠 Elaris Baseline & Lock-Management", 
        bg="#111", fg="#00ffcc", font=("Consolas", 15, "bold")
    ).pack(pady=5)

    textbox = scrolledtext.ScrolledText(root, width=90, height=23, bg="#222", fg="#0ff", font=("Consolas", 10))
    textbox.pack(padx=10, pady=10)

    btn_frame = tk.Frame(root, bg="#111")
    btn_frame.pack(pady=10)

    tk.Button(btn_frame, text="🔍 Status prüfen", command=lambda: show_status(textbox, header_label),
              bg="#0a0", fg="white", width=20).grid(row=0, column=0, padx=5)
    tk.Button(btn_frame, text="🧩 Integrität prüfen", command=lambda: verify_integrity_report(textbox),
              bg="#06a", fg="white", width=20).grid(row=0, column=1, padx=5)
    tk.Button(btn_frame, text="🧠 Autorisierter Reset", command=run_reset_secure,
              bg="#660", fg="white", width=20).grid(row=1, column=0, pady=5)
    tk.Button(btn_frame, text="⚠️ Lock entfernen",
              command=lambda: run_unlock_force(textbox, header_label),
              bg="#a00", fg="white", width=20).grid(row=1, column=1, pady=5)
    tk.Button(btn_frame, text="🚪 Schließen", command=root.destroy,
              bg="#333", fg="white", width=20).grid(row=2, column=0, columnspan=2, pady=10)

    show_status(textbox, header_label)
    root.mainloop()

if __name__ == "__main__":
    open_console()
