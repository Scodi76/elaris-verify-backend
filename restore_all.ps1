# ========================================
# 🔁 Elaris: Automatische Wiederherstellung aller .enc-Dateien vom USB-Stick
# ========================================

$usb = "D:\System Volume Information"
$base = "C:\Users\mnold_t1ohvc3\Documents\neue_KI_chatGPT_Elaris\Elairs_gatekeeper"
$tool_dir = Join-Path $base "Tools\protection"
$tool_path = Join-Path $tool_dir "usb_protection.py"

# === Prüfen, ob usb_protection.py existiert ===
if (!(Test-Path $tool_path)) {
    Write-Host "[INFO] usb_protection.py nicht gefunden. Erstelle lokale Kopie..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $tool_dir -Force | Out-Null

    $usb_protection_code = @'
#!/usr/bin/env python3
import argparse, os, json, hashlib, sys, getpass, ctypes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

def get_volume_serial(drive_letter: str) -> str:
    drive = drive_letter if drive_letter.endswith("\\") else drive_letter + "\\"
    kernel32 = ctypes.windll.kernel32
    vol_name_buf = ctypes.create_unicode_buffer(1024)
    fs_name_buf = ctypes.create_unicode_buffer(1024)
    serial_number = ctypes.c_uint(0)
    if kernel32.GetVolumeInformationW(drive, vol_name_buf, 1024,
                                      ctypes.byref(serial_number), None, None,
                                      fs_name_buf, 1024) == 0:
        raise PermissionError(f"Kein Zugriff auf Laufwerk {drive_letter}")
    return format(serial_number.value, "08x")

def derive_key(password, vol_hex):
    salt = bytes.fromhex(vol_hex)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200000, backend=default_backend())
    return kdf.derive(password.encode())

def decrypt_file(inf, outf, key):
    with open(inf, "rb") as f: blob = f.read()
    nonce, ct = blob[:12], blob[12:]
    data = AESGCM(key).decrypt(nonce, ct, None)
    with open(outf, "wb") as f: f.write(data)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    pd = sub.add_parser("dec")
    pd.add_argument("--drive", required=True)
    pd.add_argument("--in-file", required=True)
    pd.add_argument("--out-dir", required=False)
    args = p.parse_args()

    if args.cmd == "dec":
        pw = input("Bitte Entschluesselungs-Passwort eingeben (sichtbar): ")
        vol = get_volume_serial(args.drive)
        meta = args.in_file + ".meta.json"
        with open(meta, "r", encoding="utf-8") as f: j = json.load(f)
        if j.get("volume_serial") != vol:
            print("FEHLER: Volume-Serial stimmt nicht überein."); sys.exit(3)
        key = derive_key(pw, vol)
        out_dir = args.out_dir or os.path.dirname(args.in_file)
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, j.get("original_name", "restored.txt"))
        decrypt_file(args.in_file, out_file, key)
        if sha256_file(out_file) == j.get("sha256_plain"):
            print("[OK] Entschlüsselt:", out_file)
        else:
            print("[WARN] SHA-Prüfung fehlgeschlagen:", out_file)

if __name__ == "__main__":
    main()
'@

    $usb_protection_code | Out-File -FilePath $tool_path -Encoding utf8 -Force
    Write-Host "[OK] usb_protection.py erfolgreich erstellt unter $tool_path" -ForegroundColor Green
}

# === Schritt 2: Liste der zu entschlüsselnden Dateien ===
$encFiles = @(
    @{Name="HS_Final_first.txt.enc"; Target="data"},
    @{Name="KonDa_Final_first.txt.enc"; Target="data"},
    @{Name="Start_final_first.txt.enc"; Target="data"},
    @{Name="usb_protection.py.enc"; Target="Tools\protection"},
    @{Name="protection_anchor.py.enc"; Target="Tools\protection"}
)

# === Schritt 3: Entschlüsselungs-Schleife ===
foreach ($file in $encFiles) {
    $inFile = Join-Path $usb $file.Name
    $target = Join-Path $base $file.Target
    if (!(Test-Path $inFile)) {
        Write-Host "[WARN] Datei nicht gefunden auf USB: $($file.Name)" -ForegroundColor Yellow
        continue
    }
    Write-Host "`n📄 Entschlüssele $($file.Name)..." -ForegroundColor Cyan
    python $tool_path dec --drive D: --in-file "$inFile" --out-dir "$target"
}

Write-Host "`n✅ Alle Wiederherstellungsprozesse abgeschlossen." -ForegroundColor Green
# ========================================
