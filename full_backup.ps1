# ========================================
# 🔒 Elaris Vollschutz - Komplettsicherung (mit Upload-Archiv)
# ========================================

$base = "C:\Users\mnold_t1ohvc3\Documents\neue_KI_chatGPT_Elaris\Elairs_gatekeeper"
$usb = "D:\System Volume Information"
$backup_dir = "$usb\FULL_BACKUP"
$uploads_dir = Join-Path $base "uploads"
$drive = "D:"

# Passwort manuell eingeben (sichtbar)
$pw = Read-Host "Bitte Backup-Passwort eingeben (sichtbar)"

Write-Host "`n📁 Starte Vollsicherung auf $usb..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path $backup_dir -Force | Out-Null

# === SCHRITT 1: Uploads-Ordner archivieren ===
if (Test-Path $uploads_dir)
{
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $zip_name = "uploads_backup_$timestamp.zip"
    $zip_path = Join-Path $backup_dir $zip_name

    Write-Host "📦 Archiviere Uploads-Ordner nach $zip_path ..." -ForegroundColor Yellow
    Compress-Archive -Path "$uploads_dir\*" -DestinationPath $zip_path -Force
    Write-Host "✅ Uploads-Archiv erstellt: $zip_name" -ForegroundColor Green
}
else
{
    Write-Host "⚠️ Kein Uploads-Ordner gefunden, überspringe Archivierung." -ForegroundColor DarkYellow
}

# === SCHRITT 2: Dateien zur Verschlüsselung ===
$main_files = @(
    "gatekeeper.py", "signature_guard.py", "auto_gatekeeper_run.py",
    "upload_gatekeeper.py", "verify_acl.py", "verify_integrity.py",
    "verify_signature.py", "audit_trail.json", "clean_log.txt", "clean_first_config.json"
)

$data_files = @(
    "data\HS_Final_first.txt", "data\KonDa_Final_first.txt", "data\Start_final_first.txt"
)

$tool_files = @(
    "Tools\signiere_koda.py", "Tools\signiere_koda_hidden.py",
    "Tools\signiere_hs.py", "Tools\signiere_hs_hidden.py",
    "Tools\protection\protection_anchor.py", "Tools\protection\usb_protection.py"
)

$backend_files = @("elaris_verify_backend\app_verify_backend_v5_9.py")

$all_files = $main_files + $data_files + $tool_files + $backend_files

# === SCHRITT 3: Verschlüsselung durchführen ===
foreach ($file in $all_files)
{
    $src = Join-Path $base $file
    if (Test-Path $src)
    {
        Write-Host "[+] Sichere & verschlüssele $file ..." -ForegroundColor Cyan
        python "$base\Tools\protection\usb_protection.py" enc --drive $drive --out-dir $backup_dir --password $pw "$src"
    }
    else
    {
        Write-Host "[WARN] Datei fehlt: $file" -ForegroundColor DarkYellow
    }
}

Write-Host "`n✅ Vollsicherung abgeschlossen. Gespeichert unter: $backup_dir" -ForegroundColor Green
# ========================================
