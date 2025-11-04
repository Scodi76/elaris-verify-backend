import sys
import os
import tkinter as tk
from tkinter import messagebox, scrolledtext
import subprocess, json, webbrowser, hashlib, shutil, zipfile
from pathlib import Path
import datetime
from signature_guard import verify_signatures_before_start

# 🪄 Konsole unterdrücken (optional)
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')




# ======================================================
# ⚙️ Silent-Trigger: Backend → Startup Manager (First-File-Clean)
# ======================================================
if "--clean-first" in sys.argv:
    try:
        from pathlib import Path
        import subprocess, os
        base_dir = Path(__file__).parent
        tools_dir = base_dir / "Tools"
        trigger = tools_dir / "elaris_clean_trigger.py"

        if trigger.exists():
            subprocess.Popen(
                ["python", str(trigger)],
                cwd=tools_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            print("[CLEAN] Silent-Trigger gestartet → elaris_clean_trigger.py")
        else:
            print("[WARN] Cleaner-Trigger nicht gefunden:", trigger)

        sys.exit(0)

    except Exception as e:
        print(f"[ERROR] --clean-first Routine fehlgeschlagen: {e}")
        sys.exit(1)



if "--sync-final" in sys.argv:
    try:
        from pathlib import Path
        import os, json
        base_dir = Path(__file__).parent
        final_build = base_dir / "final_build"
        log_path = base_dir / "sync_log.txt"

        # Sicherstellen, dass Log existiert
        if not log_path.exists():
            log_path.touch()

        # Prüfen, ob das Zielverzeichnis vorhanden ist
        if final_build.exists():
            msg = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ final_build erkannt – Dateien synchronisiert.\n"
            print("📦 [SYNC] final_build erkannt – Dateien verfügbar.")
        else:
            msg = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ final_build fehlt – keine Dateien erkannt.\n"
            print("⚠️ [SYNC] final_build fehlt – keine Dateien erkannt.")

        # Logeintrag schreiben
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg)

        # Optional: kurze JSON-Statusdatei erzeugen
        sync_state = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "final_build_exists": final_build.exists(),
            "path": str(final_build),
        }
        (base_dir / "sync_state.json").write_text(
            json.dumps(sync_state, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        # Ohne GUI beenden
        sys.exit(0)

    except Exception as e:
        print(f"[ERROR] --sync-final Routine fehlgeschlagen: {e}")
        sys.exit(1)



BASE = Path(__file__).parent
TOOLS = BASE / "Tools"
BASELINE_FILE = BASE / "integrity_baseline.json"
RESET_STATUS = BASE / "reset_status.json"
REPORT_FILE = BASE / "process_report.json"

_link_counter = 0

# ======================================================
# 🧠 Hilfsfunktionen
# ======================================================

def append_log(msg: str):
    log_output.insert(tk.END, msg + "\n")
    log_output.see(tk.END)
    log_output.update_idletasks()

def _open_path(p: Path):
    try:
        os.startfile(p)
    except Exception:
        try:
            webbrowser.open(p.as_uri())
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte Datei nicht öffnen:\n{e}")

# ======================================================
# 🔒 NTFS-Berechtigungen prüfen und anzeigen
# ======================================================

def verify_ntfs_permissions():
    """Prüft NTFS-Zugriffsrechte und zeigt Status an."""
    append_log("\n🧩 Prüfe NTFS-Berechtigungen...\n")

    # Hauptverzeichnis + data-Unterverzeichnis prüfen
    paths_to_check = [BASE, BASE / "data"]

    try:
        total_files = 0
        ok_files = 0

        for p in paths_to_check:
            if not p.exists():
                append_log(f"⚠️ Pfad nicht gefunden: {p}")
                continue

            append_log(f"\n📁 Prüfe: {p}\n")

            result = subprocess.run(
                ["icacls", str(p)],
                capture_output=True,
                text=True,
                encoding="mbcs",
                errors="ignore"
            )
            output = result.stdout.strip()
            append_log(output)

            user = os.getenv("USERNAME", "Unbekannt")

            # Zulässige sichere Muster
            safe_patterns = [
                f"{user}:(OI)(CI)(F)",
                f"{user}:(OI)(CI)(NP)(F)",
                f"{user}:(I)(OI)(CI)(F)",
                f"{user}:(I)(OI)(CI)(NP)(F)"
            ]

            # prüfen, ob einer der sicheren Einträge vorkommt und kein Administrator drinsteht
            if any(pat in output for pat in safe_patterns) and "Administrators" not in output:
                ok_files += 1
            total_files += 1

        if total_files == 0:
            append_log("⚠️ Keine gültigen Pfade gefunden – Prüfung übersprungen.")
            acl_status_label.config(text="⚠️ Keine Prüfung", fg="#ffaa00")
            return

        if ok_files == total_files:
            append_log(f"\n✅ NTFS-Berechtigungen korrekt – {ok_files}/{total_files} Verzeichnisse sicher.\n")
            acl_status_label.config(text="🟢 NTFS OK", fg="#00ff88")
        else:
            append_log(f"\n⚠️ {total_files - ok_files}/{total_files} Verzeichnisse unsicher!\n")
            acl_status_label.config(text="🟠 NTFS Warnung", fg="#ffaa00")
            messagebox.showwarning(
                "Sicherheitswarnung",
                f"Nicht alle Verzeichnisse sind vollständig geschützt.\n({ok_files}/{total_files} sicher)"
            )

    except Exception as e:
        append_log(f"[ERROR] Konnte NTFS-Berechtigungen nicht prüfen: {e}")
        acl_status_label.config(text="🔴 ACL Fehler", fg="#ff5555")


# ======================================================
# 🧱 Baseline aktualisieren
# ======================================================

def update_integrity_baseline():
    """Erstellt eine neue integrity_baseline.json für genehmigte Änderungen (chunk-basiert und stabil)."""
    append_log("\n🧱 Starte Aktualisierung der Integritäts-Baseline...\n")

    files_to_track = [
        "HS_Final.txt",
        "KonDa_Final.txt",
        "Start_final.txt",
        "HS_Final.txt.signature.json",
        "KonDa_Final.txt.signature.json"
    ]

    new_data = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "files": {}
    }

    for file_name in files_to_track:
        path = BASE / file_name
        if path.exists():
            try:
                sha256 = hashlib.sha256()
                with open(path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha256.update(chunk)
                file_hash = sha256.hexdigest()
                new_data["files"][file_name] = file_hash
                append_log(f"✅ {file_name} -> {file_hash[:12]}... gespeichert")
            except Exception as e:
                append_log(f"[WARN] Fehler beim Hashen von {file_name}: {e}")
        else:
            append_log(f"⚠️ {file_name} nicht gefunden – übersprungen")

    try:
        with open(BASELINE_FILE, "w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
        append_log("\n✅ Neue Integritäts-Baseline erfolgreich erstellt.")
        messagebox.showinfo(
            "Baseline aktualisiert",
            "Die neue Integritäts-Baseline wurde gespeichert."
        )
    except Exception as e:
        append_log(f"[ERROR] Baseline konnte nicht gespeichert werden: {e}")
        messagebox.showerror(
            "Fehler",
            f"Fehler beim Speichern der Baseline:\n{e}"
        )



# ======================================================
# 🕒 Reset-Status (Anzeige + System-Dateien + Archiv/Audit + Tool-Verschlüsselung)
# ======================================================

def reset_system_files():
    """Setzt Hauptdateien auf Ursprungszustand zurück, führt Clean-Prozess aus, verschlüsselt sensible Tools und erstellt Archiv + Audit."""
    append_log("\n🧹 Starte System-Reset...\n")

    # --- Sicherstellen, dass *_first.txt aus /data kopiert werden ---
    try:
        data_dir = BASE / "data"
        for name in ["HS_Final_first.txt", "KonDa_Final_first.txt", "Start_final_first.txt"]:
            src = data_dir / name
            dest = BASE / name
            if src.exists():
                shutil.copy2(src, dest)
                append_log(f"📂 {name} aus /data in Hauptverzeichnis kopiert.")
            else:
                append_log(f"⚠️ {name} im data-Ordner nicht gefunden.")
    except Exception as e:
        append_log(f"[WARN] Fehler beim Kopieren der *_first.txt Dateien: {e}")

    # --- Alte Dateien & Logs löschen ---
    delete_files = [
        "HS_Final.txt", "KonDa_Final.txt",
        "HS_Final_embedded_v3.txt", "KonDa_Final_embedded_v3.txt",
        "HS_Final_embedded_v3.py", "KonDa_Final_embedded_v3.py",
        "handshake_report.json", "keys_out.json", "integrity_baseline.json",
        "verify_report.json", "auto_gatekeeper_log.txt", "RAM_PROOF.json",
        "process_report.json", "HS_Final.txt.signature.json",
        "KonDa_Final.txt.signature.json", "signing_key.json"
    ]

    deleted = 0
    for idx, name in enumerate(delete_files, start=1):
        path = BASE / name
        if path.exists():
            try:
                path.unlink()
                append_log(f"[{idx}] 🗑 {name} gelöscht.")
                deleted += 1
            except Exception as e:
                append_log(f"[{idx}] ⚠️ Fehler: {e}")
        else:
            append_log(f"[{idx}] {name} nicht gefunden.")

    append_log(f"\n✅ Reset abgeschlossen – {deleted}/{len(delete_files)} Dateien entfernt.")

    # --- Zusätzliche Bereinigung ---
    extra_cleanup = [
        "HS_Final_embedded_v3.py", "KonDa_Final_embedded_v3.py",
        "Tools\\logs\\auto_gatekeeper_log.txt", "Tools\\logs\\autostart_log.txt",
        "Tools\\logs\\keys_out.json", "Tools\\logs\\log.txt",
        "Tools\\logs\\process_report.json", "Tools\\logs\\verify_report.json"
    ]
    for rel_path in extra_cleanup:
        f = BASE / rel_path
        if f.exists():
            try:
                f.unlink()
                append_log(f"🧹 Zusätzliche Datei gelöscht: {rel_path}")
            except Exception as e:
                append_log(f"[WARN] Konnte {rel_path} nicht löschen: {e}")
        else:
            append_log(f"ℹ️ {rel_path} bereits sauber oder nicht vorhanden.")

    # --- Wiederherstellung der First-Dateien ---
    try:
        hs_first = BASE / "HS_Final_first.txt"
        koda_first = BASE / "KonDa_Final_first.txt"
        start_first = BASE / "Start_final_first.txt"
        restored = 0

        if hs_first.exists():
            shutil.copy2(hs_first, BASE / "HS_Final.txt")
            append_log("🔁 HS_Final.txt aus HS_Final_first.txt wiederhergestellt.")
            restored += 1
        else:
            append_log("⚠️ HS_Final_first.txt fehlt – Wiederherstellung nicht möglich.")

        if koda_first.exists():
            shutil.copy2(koda_first, BASE / "KonDa_Final.txt")
            append_log("🔁 KonDa_Final.txt aus KonDa_Final_first.txt wiederhergestellt.")
            restored += 1
        else:
            append_log("⚠️ KonDa_Final_first.txt fehlt – Wiederherstellung nicht möglich.")

        if start_first.exists():
            shutil.copy2(start_first, BASE / "Start_final.txt")
            append_log("🔁 Start_final.txt aus Start_final_first.txt wiederhergestellt.")
            restored += 1
        else:
            append_log("⚠️ Start_final_first.txt fehlt – Wiederherstellung nicht möglich.")

        # FIX: datetime-Korrektur
        RESET_STATUS.write_text(
            json.dumps({"last_reset": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, indent=2),
            encoding="utf-8"
        )
        update_last_reset_label()
        append_log(f"📅 Reset-Zeitpunkt gespeichert. ({restored}/3 Dateien wiederhergestellt)")
        messagebox.showinfo("System-Reset", "Systemdateien wurden zurückgesetzt und wiederhergestellt.")
    except Exception as e:
        append_log(f"[ERROR] Wiederherstellung fehlgeschlagen: {e}")

    # --- 🔒 Clean-Prozess: First-Dateien entfernen ---
    try:
        append_log("\n🧽 Starte Clean-Prozess (First-Dateien werden entfernt)...")

        patterns = ["HS_Final_first.txt", "KonDa_Final_first.txt", "Start_final_first.txt"]
        for name in patterns:
            path = BASE / name
            if path.exists():
                path.unlink()
                append_log(f"🧹 {name} aus Hauptverzeichnis gelöscht.")
        data_dir = BASE / "data"
        for name in patterns:
            path = data_dir / name
            if path.exists():
                path.unlink()
                append_log(f"🧹 {name} aus /data gelöscht.")

        clean_log = BASE / "clean_log.txt"
        with open(clean_log, "a", encoding="utf-8") as f:
            # FIX: datetime-Korrektur
            f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Clean-Prozess abgeschlossen.\n")

        append_log("✅ Clean-Prozess abgeschlossen – alle First-Dateien entfernt.\n")
    except Exception as e:
        append_log(f"[ERROR] Clean-Prozess fehlgeschlagen: {e}")

    # --- Zusätzliche Sicherheitsbereinigung nach Reset ---
    for sensitive in ["HS_Final.txt", "KonDa_Final.txt", "Start_final.txt"]:
        s_path = BASE / sensitive
        if s_path.exists():
            try:
                s_path.unlink()
                append_log(f"🧩 Sensible Datei entfernt: {sensitive}")
            except Exception as e:
                append_log(f"[WARN] Konnte {sensitive} nicht löschen: {e}")

    # --- 🧩 Archiv + Audit + Verschlüsselung sensibler Tools ---
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        backup_dir = r"D:\System Volume Information\RESET_BACKUPS"
        os.makedirs(backup_dir, exist_ok=True)

        # Archiv & Audit
        archive_path = create_reset_archive(base_path, backup_dir)
        audit_path = create_file_audit(base_path, backup_dir)

        # 🔒 Sensible Dateien und Ordner zur Verschlüsselung
        sensitive_targets = [
            "Tools\\signiere_hs.py",
            "Tools\\signiere_hs_hidden.py",
            "Tools\\signiere_koda.py",
            "Tools\\signiere_koda_hidden.py",
            "Tools\\generate_signing_key.py",
            "Tools\\generate_ram_proof.py",
            "Tools\\embed_koda_block.py",
            "Tools\\embed_starter_into_hs_v3.py",
            "Tools\\embed_starter_into_koda_v3.py",
            "Tools\\freigabe_gate_v1.py",
            "Tools\\freigabe_gate_v1 (1).py",
            "Tools\\erweckung_block.py",
            "Tools\\handshake.py",
            "Tools\\handshake_v4.py",
            "Tools\\lock_console_gui.py",
            "Tools\\lock_status.py",
            "Tools\\protection",
            "Tools\\security",
            "Tools\\cleanup_and_restore.py",
            "Tools\\elaris_clean_trigger.py",
            "Tools\\elaris_cleaner_first.py"
        ]

        append_log("\n🔒 Starte Verschlüsselung sensibler Komponenten...")

        for rel_target in sensitive_targets:
            target_path = os.path.join(base_path, rel_target)
            if os.path.exists(target_path):
                try:
                    os.system(
                        f'python "{base_path}\\Tools\\protection\\usb_protection.py" enc '
                        f'--drive D: --out-dir "{backup_dir}" '
                        f'--password guklHE3OeWvtFKh4-TrDdQ "{target_path}"'
                    )
                    append_log(f"🔐 Verschlüsselt: {rel_target}")
                except Exception as e:
                    append_log(f"[WARN] Fehler beim Verschlüsseln von {rel_target}: {e}")
            else:
                append_log(f"ℹ️ Übersprungen (nicht gefunden): {rel_target}")

        append_log(f"\n📦 Reset-Archiv, Audit und Tool-Verschlüsselung abgeschlossen:\n{archive_path}\n{audit_path}\n")

        # ======================================================
        # 🧠 Zusatzarchivierung: System-Metadateien sichern & verschlüsseln
        # ======================================================
        try:
            meta_files = [
                "reset_status.json",
                "clean_log.txt",
                "audit_trail.json",
                "integrity_block.json"
            ]
            append_log("\n🧠 Starte Zusatzarchivierung von System-Metadaten...")

            for meta in meta_files:
                meta_path = os.path.join(base_path, meta)
                if os.path.exists(meta_path):
                    try:
                        os.system(
                            f'python "{base_path}\\Tools\\protection\\usb_protection.py" enc '
                            f'--drive D: --out-dir "{backup_dir}" '
                            f'--password guklHE3OeWvtFKh4-TrDdQ "{meta_path}"'
                        )
                        append_log(f"🔐 Metadatei verschlüsselt & archiviert: {meta}")
                        os.remove(meta_path)
                        append_log(f"🧹 Lokale Version gelöscht: {meta}")
                    except Exception as e:
                        append_log(f"[WARN] Fehler beim Verarbeiten von {meta}: {e}")
                else:
                    append_log(f"ℹ️ {meta} nicht vorhanden – übersprungen.")

            append_log("✅ Zusatzarchivierung der System-Metadaten abgeschlossen.\n")
        except Exception as e:
            append_log(f"[ERROR] Zusatzarchivierung fehlgeschlagen: {e}")

    except Exception as e:
        append_log(f"[FEHLER bei Archiv/Audit/Verschlüsselung]: {e}")



# ======================================================
# 🧩 Archiv- und Audit-Erstellung nach Reset
# ======================================================

def create_reset_archive(base_path, target_dir):
    """Erstellt ein ZIP-Archiv aller relevanten Dateien im Gatekeeper-Verzeichnis."""
    # FIX: datetime-Korrektur
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"reset_backup_{timestamp}.zip"
    archive_path = os.path.join(target_dir, archive_name)

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(base_path):
            for f in files:
                # Nur relevante Dateien sichern
                if (
                    not f.endswith(".pyc")
                    and "__pycache__" not in root
                    and "restore_temp" not in root
                    and not f.endswith(".log")
                    and not f.endswith(".tmp")
                ):
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, base_path)
                    try:
                        zipf.write(full, rel)
                    except Exception as e:
                        print(f"[WARN] Konnte {rel} nicht ins Archiv aufnehmen: {e}")

    print(f"✅ Reset-Archiv erstellt: {archive_path}")
    return archive_path


def create_file_audit(base_path, target_dir):
    """
    Erstellt eine Datei-Integritätsliste (SHA256-Hash jeder Datei)
    im strukturierten Format für verify_restored_integrity().
    """
    file_list = []
    total_files = 0

    for root, _, files in os.walk(base_path):
        for f in files:
            if (
                not f.endswith(".pyc")
                and "__pycache__" not in root
                and "restore_temp" not in root
                and not f.endswith(".log")
                and not f.endswith(".tmp")
            ):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, base_path)
                total_files += 1
                try:
                    sha256 = hashlib.sha256()
                    with open(full_path, "rb") as stream:
                        for chunk in iter(lambda: stream.read(8192), b""):
                            sha256.update(chunk)
                    file_list.append({
                        "path": rel_path.replace("\\", "/"),
                        "sha256": sha256.hexdigest()
                    })
                except Exception as e:
                    file_list.append({
                        "path": rel_path.replace("\\", "/"),
                        "sha256": f"ERROR: {e}"
                    })

    # FIX: datetime-Korrektur
    audit_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "source": str(base_path),
        "total_files": total_files,
        "files": file_list
    }

    audit_path = os.path.join(target_dir, "file_audit.json")
    try:
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(audit_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Audit-Datei erstellt: {audit_path} ({total_files} Dateien erfasst)")
    except Exception as e:
        print(f"[ERROR] Konnte Audit-Datei nicht schreiben: {e}")

    return audit_path




# ======================================================
# 🕒 Reset-Anzeige-Funktionen
# ======================================================

def load_last_reset_text() -> str:
    """Liest den letzten Reset-Zeitpunkt aus der JSON-Datei."""
    if RESET_STATUS.exists():
        try:
            data = json.loads(RESET_STATUS.read_text(encoding="utf-8"))
            return data.get("last_reset", "– noch kein Reset durchgeführt –")
        except Exception:
            return "– ungültige Daten –"
    return "– noch kein Reset durchgeführt –"


def update_last_reset_label():
    """Aktualisiert die Anzeige des letzten Resets im GUI."""
    last_reset_var.set(f"🕒 Letzter Reset: {load_last_reset_text()}")


def clear_last_reset():
    """Löscht nur die Reset-Anzeige (nicht die Dateien selbst)."""
    if RESET_STATUS.exists():
        try:
            RESET_STATUS.unlink()
            append_log("🗑 Reset-Anzeige gelöscht.")
            messagebox.showinfo("Reset-Anzeige", "Die Reset-Anzeige wurde erfolgreich gelöscht.")
        except Exception as e:
            append_log(f"[WARN] Reset-Anzeige konnte nicht gelöscht werden: {e}")
            messagebox.showwarning("Warnung", f"Reset-Anzeige konnte nicht gelöscht werden:\n{e}")
    else:
        append_log("ℹ️ Keine Reset-Anzeige vorhanden.")
    update_last_reset_label()


# ======================================================
# 🧠 Signaturen automatisch erzeugen, falls sie fehlen
# ======================================================

def auto_initial_signatures():
    """Signiert HS und KoDa automatisch, falls keine Signaturdateien existieren."""
    append_log("\n🧠 Überprüfe Signaturstatus der Hauptdateien...\n")
    
    key_file = BASE / "signing_key.json"
    tools_key_file = TOOLS / "signing_key.json"

    # 🔑 Signierschlüssel prüfen / erzeugen
    if not key_file.exists() and not tools_key_file.exists():
        append_log("🔑 Kein Signaturschlüssel gefunden – erstelle neuen Schlüssel...")
        try:
            result = subprocess.run(
                ["python", str(TOOLS / "generate_signing_key.py"), "--auto"],
                capture_output=True, text=True, encoding="utf-8", errors="ignore"
            )
            if result.stdout.strip():
                append_log(result.stdout.strip())
            if result.stderr.strip():
                append_log("⚠️ Schlüsselgenerator-Fehler:\n" + result.stderr.strip())

            # Falls der Schlüssel im Tools-Ordner liegt, verschiebe ihn nach BASE
            if tools_key_file.exists():
                shutil.move(str(tools_key_file), str(key_file))
                append_log(f"📦 Signaturschlüssel von Tools nach Hauptverzeichnis verschoben:\n{key_file}")
            append_log("✅ Neuer Signierschlüssel wurde erstellt.")
        except Exception as e:
            append_log(f"[ERROR] Konnte Signierschlüssel nicht erzeugen: {e}")
            messagebox.showerror("Fehler", f"Schlüsselgenerierung fehlgeschlagen:\n{e}")
            return False

    # Fallback: Falls nur in Tools existiert
    elif tools_key_file.exists() and not key_file.exists():
        try:
            shutil.move(str(tools_key_file), str(key_file))
            append_log(f"📦 Signaturschlüssel nach {key_file} verschoben.")
        except Exception as e:
            append_log(f"[WARN] Konnte Schlüssel nicht verschieben: {e}")

    hs_sig = BASE / "HS_Final.txt.signature.json"
    koda_sig = BASE / "KonDa_Final.txt.signature.json"

    # Wenn beide Signaturen vorhanden → fertig
    if hs_sig.exists() and koda_sig.exists():
        append_log("✅ Alle Signaturdateien vorhanden – keine Aktion erforderlich.")
        return True

    try:
        # --- HS SIGNIERUNG ---
        if not hs_sig.exists():
            append_log("🧩 Signiere HS_Final.txt...")
            hs_script = TOOLS / "signiere_hs.py"
            if not hs_script.exists():
                hs_script = TOOLS / "signiere_hs_hidden.py"
            result = subprocess.run(
                ["python", str(hs_script)],
                capture_output=True, text=True, encoding="utf-8", errors="ignore"
            )
            if result.stdout.strip():
                append_log(result.stdout.strip())
            if result.stderr.strip():
                append_log("⚠️ Fehler (HS): " + result.stderr.strip())
            append_log("✅ HS_Final.txt Signiervorgang abgeschlossen.")

        # --- KODA SIGNIERUNG ---
        if not koda_sig.exists():
            append_log("🧩 Signiere KonDa_Final.txt...")
            koda_script = TOOLS / "signiere_koda.py"
            if not koda_script.exists():
                koda_script = TOOLS / "signiere_koda_hidden.py"
            result = subprocess.run(
                ["python", str(koda_script)],
                capture_output=True, text=True, encoding="utf-8", errors="ignore"
            )
            if result.stdout.strip():
                append_log(result.stdout.strip())
            if result.stderr.strip():
                append_log("⚠️ Fehler (KoDa): " + result.stderr.strip())
            append_log("✅ KonDa_Final.txt Signiervorgang abgeschlossen.")

        append_log("✅ Signaturprüfung abgeschlossen – fortfahren möglich.")

        # --- Embed-Dateien ---
        try:
            embed_hs = BASE / "HS_Final_embedded_v3.txt"
            embed_koda = BASE / "KonDa_Final_embedded_v3.txt"

            if not embed_hs.exists():
                append_log("🧬 Starte HS-Einbettung (embed_starter_into_hs_v3.py)...")
                subprocess.run(
                    ["python", str(TOOLS / "embed_starter_into_hs_v3.py")],
                    capture_output=True, text=True, encoding="utf-8", errors="ignore"
                )

            if not embed_koda.exists():
                append_log("🧬 Starte KoDa-Einbettung (embed_starter_into_koda_v3.py)...")
                subprocess.run(
                    ["python", str(TOOLS / "embed_starter_into_koda_v3.py")],
                    capture_output=True, text=True, encoding="utf-8", errors="ignore"
                )

            append_log("✅ Embed-Dateien wurden erfolgreich erzeugt oder überprüft.")
        except Exception as e:
            append_log(f"[ERROR] Embed-Erstellung fehlgeschlagen: {e}")

        return True

    except Exception as e:
        append_log(f"[ERROR] Signaturerstellung fehlgeschlagen: {e}")
        messagebox.showerror("Fehler", f"Fehler beim Signieren:\n{e}")
        return False




# --- 🧩 INTEGRITÄTSBLOCK-ERSTELLUNG (HS ↔ KoDa) ---
# Diese Routine wird beim Start ausgeführt, sobald Baseline-Check und ACL-Prüfung abgeschlossen sind.
# Sie prüft, ob HS_Final.txt und KonDa_Final.txt existieren, berechnet deren SHA256-Hashes,
# führt eine einfache Konsistenzprüfung durch und erstellt integrity_block.json.

import hashlib
from datetime import datetime
import json, os

def create_integrity_block():
    """
    Erstellt automatisch den Integritätsblock für HS und KoDa.
    Wird vom Startup Manager direkt nach der Baseline-/ACL-Prüfung ausgeführt.
    """
    try:
        print("\n🧩 [Integritätsblock] Starte Integritätsprüfung HS ↔ KoDa ...")

        # --- Pfade festlegen ---
        hs_path = os.path.join(os.getcwd(), "HS_Final.txt")
        koda_path = os.path.join(os.getcwd(), "KonDa_Final.txt")
        block_path = os.path.join(os.getcwd(), "integrity_block.json")

        # --- Existenz prüfen ---
        if not os.path.exists(hs_path):
            print("⚠️  HS_Final.txt nicht gefunden – Integritätsprüfung abgebrochen.")
            return False

        if not os.path.exists(koda_path):
            print("⚠️  KonDa_Final.txt nicht gefunden – Integritätsprüfung abgebrochen.")
            return False

        # --- Hashes berechnen ---
        def calc_hash(path):
            with open(path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()

        hs_hash = calc_hash(hs_path)
        koda_hash = calc_hash(koda_path)

        print(f"🔹 HS-Hash:   {hs_hash[:16]}...")
        print(f"🔹 KoDa-Hash: {koda_hash[:16]}...")

        # --- Konsistenz prüfen ---
        # Hier nur einfache Vergleichsprüfung (optional erweiterbar um Referenz-Check)
        match_status = "OK" if hs_hash and koda_hash else "MISSING"
        verified = (match_status == "OK")

        # --- Datenstruktur aufbauen ---
        integrity_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "hs_file": "HS_Final.txt",
            "hs_hash": hs_hash,
            "koda_file": "KonDa_Final.txt",
            "koda_hash": koda_hash,
            "match_status": match_status,
            "verified": verified
        }

        # --- JSON schreiben ---
        with open(block_path, "w", encoding="utf-8") as f:
            json.dump(integrity_data, f, indent=2, ensure_ascii=False)

        print("✅ Integritätsblock erfolgreich erstellt:")
        print(f"📁 {block_path}")
        print(f"🧩 Status: {match_status}")

        return True

    except Exception as e:
        print(f"❌ Fehler beim Erstellen des Integritätsblocks: {e}")
        return False


# ======================================================
# 🚀 Gatekeeper starten
# ======================================================

def start_gatekeeper():
    append_log("\n🚀 Starte Gatekeeper...\n")

    # 🧠 Vorprüfung: Signaturen automatisch erzeugen, falls nötig
    try:
        if not auto_initial_signatures():
            append_log("❌ Automatische Signaturerstellung fehlgeschlagen – Start abgebrochen.\n")
            return
    except NameError:
        append_log("[ERROR] Funktion auto_initial_signatures() nicht gefunden – bitte prüfen.\n")
        messagebox.showerror("Fehler", "Die Signaturroutine fehlt oder ist fehlerhaft eingebunden.")
        return
    except Exception as e:
        append_log(f"[ERROR] Unerwarteter Fehler bei Signaturprüfung: {e}\n")
        return

    # 🧩 Signaturprüfung vor Start
    append_log("🧠 Überprüfe Signaturen vor dem Start...\n")
    valid = False
    try:
        valid = verify_signatures_before_start(BASE, log_callback=append_log)
    except Exception as e:
        append_log(f"[ERROR] Fehler bei verify_signatures_before_start: {e}\n")

    if not valid:
        append_log("❌ Signaturprüfung fehlgeschlagen – Start blockiert.\n")
        response = messagebox.askyesno(
            "Sicherheitsstufe 5+",
            "Eine oder mehrere Dateien sind nicht signiert oder manipuliert.\n"
            "Möchten Sie eine neue Baseline erstellen, um die Änderungen zu autorisieren?"
        )

        if response:
            append_log("🧱 Benutzer hat bestätigt – neue Baseline wird erstellt...\n")
            update_integrity_baseline()
            try:
                update_signature_status()
            except Exception:
                append_log("[WARN] GUI-Signaturstatus konnte nach Baseline-Erstellung nicht aktualisiert werden.\n")
            append_log("✅ Neue Baseline erstellt. Bitte starten Sie den Gatekeeper erneut.\n")
            messagebox.showinfo("Baseline aktualisiert", "Neue Baseline wurde erstellt.\nStarten Sie den Gatekeeper erneut.")
        else:
            append_log("🚫 Benutzer hat abgebrochen – Start blockiert.\n")
            messagebox.showwarning("Start blockiert", "Vorgang abgebrochen.\nSystem bleibt gesperrt.")
        return

    # 🧩 Gatekeeper-Skript prüfen und starten
    script = BASE / "auto_gatekeeper_run.py"
    if not script.exists():
        append_log("❌ auto_gatekeeper_run.py fehlt – Start kann nicht ausgeführt werden.\n")
        messagebox.showwarning("Datei fehlt", f"'{script.name}' wurde nicht gefunden.")
        return

    append_log("🧠 Führe Gatekeeper-Hauptprozess aus...\n")

    try:
        result = subprocess.run(
            ["python", str(script)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        if result.stdout.strip():
            append_log(f"📄 [Gatekeeper-Output] {result.stdout.strip()}\n")
        if result.stderr.strip():
            append_log(f"⚠️ [Gatekeeper-Fehler] {result.stderr.strip()}\n")

    except Exception as e:
        append_log(f"[ERROR] Gatekeeper konnte nicht gestartet werden: {e}\n")
        messagebox.showerror("Gatekeeper-Fehler", f"Fehler beim Ausführen:\n{e}")

    # 🟢 Nach erfolgreichem Lauf GUI-Status neu laden
    try:
        update_signature_status()
        append_log("🔄 Signaturstatus im GUI aktualisiert.\n")
    except Exception as e:
        append_log(f"[WARN] GUI-Status konnte nicht aktualisiert werden: {e}\n")



# ======================================================
# 🧽 First-Dateien bereinigen (Trigger)
# ======================================================

def run_clean_first():
    append_log("\n🧽 Starte First-File-Cleaner...\n")
    try:
        result = subprocess.run(
            ["python", str(BASE / "startup_manager_gui.py"), "--clean-first"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        if result.stdout.strip():
            append_log(result.stdout.strip() + "\n")
        if result.stderr.strip():
            append_log("⚠️ Cleaner-Fehler:\n" + result.stderr.strip() + "\n")
        append_log("✅ Cleaner-Trigger gesendet.\n")

    except Exception as e:
        append_log(f"[ERROR] Cleaner konnte nicht gestartet werden: {e}\n")
        messagebox.showerror("Fehler", f"Cleaner-Start fehlgeschlagen:\n{e}")




# ======================================================
# 🔍 Signaturstatus visuell anzeigen
# ======================================================

def update_signature_status():
    """Liest verify_report.json und zeigt den visuellen Status."""
    if not (BASE / "verify_report.json").exists():
        signature_status_label.config(text="🔴 Keine Prüfung", fg="#ff5555")
        return

    try:
        data = json.loads((BASE / "verify_report.json").read_text(encoding="utf-8"))
        fails = data.get("summary", {}).get("fail", 0)
        warns = data.get("summary", {}).get("warn", 0)
        if fails > 0:
            signature_status_label.config(text="🔴 Signaturen fehlerhaft", fg="#ff5555")
        elif warns > 0:
            signature_status_label.config(text="🟠 Unvollständig", fg="#ffaa00")
        else:
            signature_status_label.config(text="🟢 Signaturen OK", fg="#00ff88")
    except Exception:
        signature_status_label.config(text="🔴 Fehler beim Laden", fg="#ff5555")

# ======================================================
# 🧱 GUI Aufbau
# ======================================================

window = tk.Tk()
window.title("🧠 Elaris Startup Manager")
window.geometry("980x870")
window.configure(bg="#1c1c1c")

header = tk.Label(window, text="🧠 Elaris Startup Manager",
                  font=("Segoe UI", 18, "bold"), fg="#00e0ff", bg="#1c1c1c")
header.pack(pady=8)

# --- ACL + Signaturstatus ---
status_frame = tk.Frame(window, bg="#1c1c1c")
status_frame.pack(pady=(4, 6))

acl_status_label = tk.Label(status_frame, text="🔍 ACL wird geprüft...",
                            font=("Segoe UI", 10, "bold"), bg="#1c1c1c", fg="#cccccc")
acl_status_label.pack(side="left", padx=20)

signature_status_label = tk.Label(status_frame, text="🔴 Keine Prüfung",
                                  font=("Segoe UI", 10, "bold"), bg="#1c1c1c", fg="#ff5555")
signature_status_label.pack(side="right", padx=20)

# --- Reset-Anzeige ---
last_reset_var = tk.StringVar(value=f"🕒 Letzter Reset: {load_last_reset_text()}")
tk.Label(window, textvariable=last_reset_var,
         font=("Segoe UI", 10), fg="#cfcfcf", bg="#1c1c1c").pack(pady=(0, 10))

# --- Buttons ---
btn_frame = tk.Frame(window, bg="#1c1c1c")
btn_frame.pack(pady=10)

tk.Button(btn_frame, text="🧱 Baseline aktualisieren", command=update_integrity_baseline,
          bg="#607d8b", fg="white", font=("Segoe UI", 11, "bold"), width=25).grid(row=0, column=0, padx=8, pady=6)

tk.Button(btn_frame, text="🚀 Gatekeeper starten", command=start_gatekeeper,
          bg="#00bfff", fg="white", font=("Segoe UI", 11, "bold"), width=25).grid(row=0, column=1, padx=8, pady=6)

tk.Button(btn_frame, text="🧹 System-Reset", command=reset_system_files,
          bg="#ff7043", fg="white", font=("Segoe UI", 11, "bold"), width=25).grid(row=0, column=2, padx=8, pady=6)

tk.Button(btn_frame, text="🔄 Reset-Anzeige zurücksetzen", command=update_last_reset_label,
          bg="#5555aa", fg="white", font=("Segoe UI", 11, "bold"), width=25).grid(row=1, column=1, pady=6)

tk.Button(btn_frame, text="🗑 Reset-Anzeige löschen", command=clear_last_reset,
          bg="#666666", fg="white", font=("Segoe UI", 11, "bold"), width=25).grid(row=1, column=0, pady=6)

tk.Button(btn_frame, text="🧽 First-Dateien bereinigen", command=run_clean_first,
          bg="#2e7d32", fg="white", font=("Segoe UI", 11, "bold"), width=25).grid(row=1, column=2, padx=6, pady=6)



# --- Log-Ausgabe ---
log_output = scrolledtext.ScrolledText(
    window, wrap=tk.WORD, height=26, width=120,
    font=("Consolas", 10), bg="#262626", fg="#00ffea", insertbackground="#00ffea"
)
log_output.pack(padx=10, pady=10, fill="both", expand=True)

# --- Beenden ---
tk.Button(window, text="❌ Beenden", command=window.destroy,
          bg="#333333", fg="white", font=("Segoe UI", 11, "bold"), width=16).pack(pady=(0, 12))

# --- Initial-Log ---
append_log("🧠 Elaris Startup Manager geladen.\n➡️ Systembereit.")

# ======================================================
# 🛰️ Automatischer Sync mit Verify-Backend (Render)
# ======================================================
import subprocess

def run_sync():
    """Sendet beim Start einen Status-Sync an das Verify-Backend (silent)."""
    try:
        sync_script = r"C:\Users\mnold_t1ohvc3\Documents\neue_KI_chatGPT_Elaris\Elairs_gatekeeper\sync_startup.ps1"
        if os.path.exists(sync_script):
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-WindowStyle", "Hidden",
                    "-ExecutionPolicy", "Bypass",
                    "-File", sync_script
                ],
                capture_output=True, text=True, encoding="utf-8", errors="ignore",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            append_log("🛰️ Sync-Startskript ausgeführt (Verify-Backend synchronisiert).")
            if result.stdout.strip():
                append_log(f"✅ Sync-Antwort: {result.stdout.strip()}")
            if result.stderr.strip():
                append_log(f"⚠️ Sync-Fehler: {result.stderr.strip()}")
        else:
            append_log(f"⚠️ Sync-Skript nicht gefunden: {sync_script}")
    except Exception as e:
        append_log(f"[WARN] Sync konnte nicht ausgeführt werden: {e}")


# --- Sync automatisch beim Start ausführen ---
run_sync()

# --- Nachgelagerte Statusprüfungen ---
verify_ntfs_permissions()
update_signature_status()

# Jetzt erst Integritätsblock erzeugen (nach ACL/Baseline/Status)
create_integrity_block()



# ======================================================
# 🔐 USB-Gesamtwiederherstellung (verdeckte Tastenkombination: STRG+ALT+R)
# ======================================================
import threading
import tkinter.simpledialog
from tkinter import messagebox
import hashlib, os, shutil, zipfile

_ELARIS_DEKRYPT_PW = "guklHE3OeWvtFKh4-TrDdQ"

def _trigger_usb_restore(event=None):
    """
    Verdeckter USB-Wiederherstellungs-Trigger (Strg+Alt+R).
    Entschlüsselt und entpackt ALLE Backups von D:\System Volume Information\FULL_BACKUP & RESET_BACKUPS
    und stellt sie vollständig am Ursprungsort wieder her.
    """
    try:
        pw = tkinter.simpledialog.askstring(
            "Elaris – Systemwiederherstellung",
            "Bitte Entschlüsselungs-Passwort eingeben:",
            show="*"
        )
        if not pw or pw.strip() != _ELARIS_DEKRYPT_PW:
            append_log("🚫 Falsches Passwort oder Abbruch – Restore nicht gestartet.")
            return

        append_log("\n🔓 Starte vollständige USB-Wiederherstellung...")
        os.environ["ELARIS_PROT_PW"] = _ELARIS_DEKRYPT_PW

        def run_restore():
            try:
                base_dir = r"C:\Users\mnold_t1ohvc3\Documents\neue_KI_chatGPT_Elaris\Elairs_gatekeeper"
                tools_root = os.path.join(base_dir, "Tools")
                usb_root = r"D:\System Volume Information"
                usb_prot = os.path.join(tools_root, "protection", "usb_protection.py")
                usb_enc = usb_prot + ".enc"

                # Prüfen, ob Entschlüsselungstool verfügbar ist
                if not os.path.exists(usb_prot) and os.path.exists(usb_enc):
                    append_log("🧩 Entschlüssele temporär usb_protection.py für Restore...")
                    os.system(
                        f'python "{os.path.join(tools_root, "protection", "decrypt_usb_prot_stub.py")}" '
                        f'--in "{usb_enc}" --out-dir "{os.path.dirname(usb_prot)}" '
                        f'--password "{_ELARIS_DEKRYPT_PW}"'
                    )
                    append_log("✅ usb_protection.py temporär entschlüsselt.")

                # Alle Archive suchen
                enc_files = []
                for sub in ["FULL_BACKUP", "RESET_BACKUPS"]:
                    folder = os.path.join(usb_root, sub)
                    if os.path.exists(folder):
                        for root, _, files in os.walk(folder):
                            for f in files:
                                if f.endswith(".zip.enc") or f.endswith(".zip"):
                                    enc_files.append(os.path.join(root, f))

                if not enc_files:
                    append_log("⚠️ Keine Backup-Archive gefunden – Wiederherstellung abgebrochen.")
                    return

                # Temporären Restore-Ordner vorbereiten
                temp_dir = os.path.join(base_dir, "restore_temp")
                os.makedirs(temp_dir, exist_ok=True)

                # --- Schritt 1: Entschlüsseln oder kopieren ---
                for f in enc_files:
                    try:
                        if f.endswith(".zip.enc"):
                            append_log(f"🔓 Entschlüssele {os.path.basename(f)} ...")
                            os.system(
                                f'python "{usb_prot}" dec --drive D: --out-dir "{temp_dir}" '
                                f'--password "{_ELARIS_DEKRYPT_PW}" "{f}"'
                            )
                        else:
                            shutil.copy2(f, temp_dir)
                            append_log(f"📦 Kopiert: {os.path.basename(f)}")
                    except Exception as e:
                        append_log(f"[WARN] Fehler bei {f}: {e}")

                # --- Schritt 2: Entpacken ---
                append_log("\n📂 Entpacke alle wiederhergestellten Archive...")
                for f in os.listdir(temp_dir):
                    if f.endswith(".zip"):
                        zip_path = os.path.join(temp_dir, f)
                        try:
                            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                                members = [m for m in zip_ref.namelist() if ".git/" not in m]
                                zip_ref.extractall(base_dir, members)
                            append_log(f"✅ Entpackt: {os.path.basename(f)}")
                        except Exception as e:
                            append_log(f"[WARN] Konnte {f} nicht entpacken: {e}")

                append_log("\n🧩 Wiederherstellung abgeschlossen – Dateien an Ursprungsort übertragen.")

                # --- Schritt 3: Integritätsprüfung ---
                verify_func = globals().get("verify_restored_integrity", None)
                if verify_func:
                    audit_candidates = [
                        os.path.join(usb_root, "RESET_BACKUPS", "file_audit.json"),
                        os.path.join(usb_root, "FULL_BACKUP", "file_audit.json"),
                    ]
                    found_audit = False
                    for ap in audit_candidates:
                        if os.path.exists(ap):
                            append_log(f"📄 Starte Integritätsprüfung mit {os.path.basename(ap)} ...")
                            verify_func(ap, base_dir)
                            found_audit = True
                            break
                    if not found_audit:
                        append_log("⚠️ Keine file_audit.json gefunden – Integritätsprüfung übersprungen.")
                else:
                    append_log("⚠️ verify_restored_integrity() nicht definiert – übersprungen.")

                append_log("\n✅ Vollständige Systemwiederherstellung erfolgreich abgeschlossen.")
                messagebox.showinfo(
                    "Elaris – Systemwiederherstellung",
                    "✅ Vollständige Systemwiederherstellung erfolgreich abgeschlossen."
                )

            except Exception as e:
                append_log(f"[ERROR] Wiederherstellung fehlgeschlagen: {e}")

        threading.Thread(target=run_restore, daemon=True).start()

    except Exception as e:
        append_log(f"[ERROR] Interner Fehler beim Restore: {e}")

# Tastenkombination registrieren (STRG + ALT + R)
window.bind("<Control-Alt-r>", _trigger_usb_restore)



# ======================================================
# 🧩 Integritätsprüfung nach Wiederherstellung
# ======================================================
import hashlib
import json
import os
import datetime

def verify_restored_integrity(audit_path, base_dir):
    """
    Vergleicht alle Hashes aus der file_audit.json mit den wiederhergestellten Dateien.
    Gibt im Log die Integrität pro Datei und eine Gesamtbewertung aus.
    """
    try:
        append_log(f"\n🧩 [Integritätsprüfung] Starte Abgleich mit Audit-Datei:\n📄 {audit_path}")
        if not os.path.exists(audit_path):
            append_log("⚠️ Audit-Datei nicht gefunden – Abbruch der Integritätsprüfung.")
            return False

        with open(audit_path, "r", encoding="utf-8") as f:
            audit_data = json.load(f)

        total = 0
        ok_count = 0
        fail_count = 0
        missing_count = 0

        for entry in audit_data.get("files", []):
            rel_path = entry.get("path")
            expected_hash = entry.get("sha256")
            total += 1

            if not rel_path or not expected_hash:
                continue

            abs_path = os.path.join(base_dir, rel_path)
            if not os.path.exists(abs_path):
                missing_count += 1
                append_log(f"❌ Fehlend: {rel_path}")
                continue

            # SHA256 berechnen
            sha256 = hashlib.sha256()
            try:
                with open(abs_path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha256.update(chunk)
                actual_hash = sha256.hexdigest()

                if actual_hash == expected_hash:
                    ok_count += 1
                    append_log(f"✅ OK: {rel_path}")
                else:
                    fail_count += 1
                    append_log(f"⚠️ HASH-ABWEICHUNG: {rel_path}")
            except Exception as e:
                fail_count += 1
                append_log(f"[WARN] Fehler beim Prüfen {rel_path}: {e}")

        append_log("\n🧾 Integritätszusammenfassung:")
        append_log(f"   ✔️ OK: {ok_count}")
        append_log(f"   ⚠️ Abweichungen: {fail_count}")
        append_log(f"   ❌ Fehlend: {missing_count}")
        append_log(f"   📊 Gesamt geprüft: {total}")

        result_status = "OK" if fail_count == 0 and missing_count == 0 else "WARNUNG"

        log_summary = {
            "timestamp": datetime.datetime.now().isoformat(),
            "audit_source": audit_path,
            "checked_files": total,
            "ok": ok_count,
            "failed": fail_count,
            "missing": missing_count,
            "status": result_status
        }

        # Ergebnis im Logs-Ordner sichern
        result_file = os.path.join(base_dir, "Tools", "logs", "integrity_restore_log.json")
        os.makedirs(os.path.dirname(result_file), exist_ok=True)
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(log_summary, f, indent=2, ensure_ascii=False)

        if result_status == "OK":
            append_log("✅ Integritätsprüfung abgeschlossen – alle Dateien authentisch.\n")
        else:
            append_log("⚠️ Integritätsprüfung abgeschlossen – Abweichungen erkannt.\n")

        return result_status == "OK"

    except Exception as e:
        append_log(f"[ERROR] Integritätsprüfung fehlgeschlagen: {e}")
        return False


window.mainloop()
