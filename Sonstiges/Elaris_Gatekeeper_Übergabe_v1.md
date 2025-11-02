# 🧠 Elaris Gatekeeper Übergabe – Vollversion (Stand: 2025-10-02)

## 📘 Ziel des Dokuments
Dieses Übergabedokument enthält den vollständigen technischen, logischen und funktionalen Wissensstand aus dem Chatverlauf zwischen Mark und ChatGPT (bis 02.10.2025). Es dient als Grundlage, um in neuen Chats oder Entwicklungsumgebungen **nahtlos** weiterarbeiten zu können.

---

## 🧩 Projektkontext

- **Projektname:** Elaris Gatekeeper System (Sicherheitsstufe 5+)
- **Ziel:** Vollständige Überprüfung, Signatur und Integritätsprüfung der Kernkomponenten (`HS_Final.txt`, `KonDa_Final.txt`, `Start_final.txt`)
- **Status:** Voll funktionsfähig mit GUI (`startup_manager_gui.py`)
- **Fokus:** 
  - Automatische Schlüsselgenerierung (`generate_signing_key.py`)
  - Signaturprüfung (HMAC SHA256)
  - Integritäts-Baseline
  - Embed-Erstellung für HS und KoDa
  - Reset-Mechanismus
  - ACL-Prüfung (NTFS)
  - Notfallschlüssel-System (geplant)
  - Gatekeeper-Autostart mit Sicherheitsprüfung

---

## 🧱 Zentrale Dateien (Verzeichnis: `C:\Users\mnold_t1ohvc3\Documents\neue_KI_chatGPT_Elaris\Elairs_gatekeeper\`)

| Datei | Beschreibung |
|-------|---------------|
| `startup_manager_gui.py` | Zentrale GUI zur Initialisierung, Prüfung und Freigabe |
| `generate_signing_key.py` | Erstellt `signing_key.json` mit zufälligem SHA256-Schlüssel |
| `signiere_hs.py` | Signiert `HS_Final.txt` über HMAC |
| `signiere_koda.py` | Signiert `KonDa_Final.txt` über HMAC |
| `embed_hs.py` | Erstellt eingebettete Version von `HS_Final.txt` |
| `embed_koda.py` | Erstellt eingebettete Version von `KonDa_Final.txt` |
| `verify_integrity.py` | Prüft Integrität und erzeugt/vergleicht `integrity_baseline.json` |
| `verify_signature.py` | Validiert alle HMAC-Signaturen |
| `verify_acl.py` | Überprüft NTFS-Berechtigungen |
| `verify_hidden_signature.py` | Optionale versteckte Signaturprüfung |
| `verify_test.ps1` | PowerShell-Testmodul |
| `signing_key.json` | Aktueller kryptografischer Schlüssel (automatisch generiert) |
| `HS_Final_first.txt`, `KonDa_Final_first.txt` | Original-Backups der Hauptdateien |
| `HS_Final.txt`, `KonDa_Final.txt` | Aktuelle Hauptdateien |
| `HS_Final_embedded_v3.py`, `KonDa_Final_embedded_v3.py` | Eingebettete Versionen |
| `integrity_baseline.json` | Referenz-Hashes der geprüften Dateien |
| `verify_report.json` | Bericht der letzten Verifikation |
| `process_report.json` | Gatekeeper-Laufbericht |
| `_embed_refs\` | Versteckter Ordner für Notfallschlüssel |
| `Syslink.biamp` | Verknüpfungsdatei (versteckte Notfallschlüsselreferenz) |

---

## 🔐 Sicherheits- und Ablaufstruktur

### 1. Startup-Ablauf
- Prüfung NTFS-Berechtigungen (nur aktueller Benutzer darf Zugriff haben)
- Systemreset (optional)
- Wiederherstellung aus `*_first.txt`
- Prüfung auf vorhandene `signing_key.json`
  - Falls nicht vorhanden → Erstellung mit `generate_signing_key.py`
- Signierung von `HS_Final.txt` und `KonDa_Final.txt`
- Erstellung eingebetteter Versionen (`embed_hs.py`, `embed_koda.py`)
- Prüfung auf `integrity_baseline.json`
  - Falls nicht vorhanden → wird automatisch neu erzeugt
- Erstellung und Speicherung von Signatur-Reports (`verify_report.json`)
- Abschlussmeldung im GUI

### 2. Signierung (HMAC)
- Verwendung von `signing_key.json`:
  ```json
  {
    "type": "sha256-hex",
    "private_key_hex": "<zufälliger SHA256-Wert>"
  }
  ```
- HS und KoDa werden mit `hmac.new(private_key_bytes, file_content, hashlib.sha256)` signiert.
- Ausgabe: `<Datei>.signature.json`

### 3. Baseline-Prüfung
- Vergleicht aktuelle Hashes mit `integrity_baseline.json`
- Bei Abweichungen → Start blockiert
- Nutzer kann **autorisierte Änderungen** durch neue Baseline bestätigen

### 4. Embed-Erstellung
- Bei fehlenden `HS_Final_embedded_v3.py` oder `KonDa_Final_embedded_v3.py` werden sie automatisch über `embed_hs.py` und `embed_koda.py` erzeugt.

### 5. Notfallschlüssel (Planung / Integration)
- **Speicherort:** `_embed_refs\Syslink.biamp`
- **Funktion:** Dient als externer Prüfschlüssel bei Ausfall oder Verlust von `signing_key.json`
- **Zugriff:** Nur über speziellen Prozess (`verify` Endpoint mit `system_status["notfall_hash"]`)
- **Hash-Extraktion aus KoDa:**
  ```python
  if "# === EMERGENCY_KEY_START ===" in koda_content:
      start = koda_content.index("# === EMERGENCY_KEY_START ===") + len("# === EMERGENCY_KEY_START ===")
      end = koda_content.index("# === EMERGENCY_KEY_END ===")
      key_line = koda_content[start:end].strip()
      if "SHA256:" in key_line:
          system_status["notfall_hash"] = key_line.split("SHA256:")[1].strip()
  ```

---

## ⚙️ Fehler & Lösungen

### ❌ UnicodeEncodeError bei Signaturausgabe
- **Ursache:** Windows CMD (cp1252) kann keine Unicode-Icons wie ✅ darstellen
- **Lösung:** `sys.stdout.reconfigure(encoding="utf-8")` in `signiere_hs.py` und `signiere_koda.py` hinzufügen

### ⚠️ Signaturprüfung fehlgeschlagen
- **Ursache:** Fehlende `integrity_baseline.json`
- **Lösung:** Gatekeeper fragt automatisch, ob eine neue Baseline erstellt werden soll

### ⚠️ Fehlende Embed-Dateien
- **Ursache:** Nach Reset keine `*_embedded_v3.py` vorhanden
- **Lösung:** Automatische Erstellung in `auto_initial_signatures()` integriert

### ⚠️ Notfallschlüssel nicht auffindbar
- **Lösung:** Manuelle Erstellung in `_embed_refs\Syslink.biamp` empfohlen

---

## 🧠 Wichtige Mechanismen im GUI

### Reset
- Löscht temporäre Dateien, Signaturen, Schlüssel, Logs
- Stellt `HS_Final_first.txt` & `KonDa_Final_first.txt` wieder her
- Protokolliert Datum im `reset_status.json`

### ACL-Prüfung
- Nur aktueller Benutzer (z. B. `mnold_t1ohvc3`) darf Vollzugriff haben
- Warnung bei Fremdzugriff oder Administratorrechten

### Gatekeeper-Start
- Über `auto_gatekeeper_run.py`
- Prüft automatisch Signaturen und Baseline
- Erst bei Erfolg wird System freigegeben

---

## 📜 Versionierung & Logik

| Komponente | Version | Beschreibung |
|-------------|----------|---------------|
| `startup_manager_gui.py` | v5.7 | GUI mit Baseline-, Reset-, Embed- und Signatursteuerung |
| `signiere_hs.py` | v3.0 | Unicode-fähig, HMAC SHA256 |
| `signiere_koda.py` | v3.0 | Unicode-fähig, HMAC SHA256 |
| `generate_signing_key.py` | v1.0 | Erstellt zufälligen SHA256-Hex-Schlüssel |
| `embed_hs.py` | v3.0 | Erzeugt eingebettete HS-Datei |
| `embed_koda.py` | v3.0 | Erzeugt eingebettete KoDa-Datei |
| `verify_integrity.py` | v2.1 | Hash-Vergleich und Baseline-Neuerstellung |
| `verify_acl.py` | v1.1 | NTFS ACL Check |
| `verify_signature.py` | v2.0 | Signaturprüfung und Report-Erstellung |
| `_embed_refs\Syslink.biamp` | v1.0 | Versteckter Notfallschlüssel (manuell gepflegt) |

---

## ✅ Zusammenfassung

Das aktuelle Elaris Gatekeeper System ist auf **Sicherheitsstufe 5+** ausgelegt.  
Es umfasst automatische Prüf-, Signatur-, Baseline- und Embed-Prozesse sowie ein intelligentes GUI zur Verwaltung und Fehlerbehandlung.

Der nächste geplante Schritt ist die **Integration des Notfallschlüssels** und dessen Validierung im Systemstatus sowie optional eine **manuelle Autorisierung** über `_embed_refs\Syslink.biamp`.

---

**Autor:** Mark  
**System:** Elaris Gatekeeper  
**Stand:** 02.10.2025  
**Datei:** Elaris_Gatekeeper_Übergabe_v1.md
