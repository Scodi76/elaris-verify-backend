# ========================================
# 🔁 Elaris Vollschutz - Wiederherstellung aus FULL_BACKUP
# ========================================

$base = "C:\Users\mnold_t1ohvc3\Documents\neue_KI_chatGPT_Elaris\Elairs_gatekeeper"
$usb = "D:\System Volume Information"
$backup_dir = "$usb\FULL_BACKUP"
$drive = "D:"

# Passwort sichtbar eingeben
$pw = Read-Host "Bitte Wiederherstellungs-Passwort eingeben (sichtbar)"

Write-Host "`n📂 Starte Wiederherstellung aus $backup_dir ..." -ForegroundColor Cyan

# === Datei-Liste definieren (Zielpfade exakt wie beim Backup) ===
$restore_map = @{
    "gatekeeper.py"                     = "$base"
    "signature_guard.py"                = "$base"
    "auto_gatekeeper_run.py"            = "$base"
    "upload_gatekeeper.py"              = "$base"
    "verify_acl.py"                     = "$base"
    "verify_integrity.py"               = "$base"
    "verify_signature.py"               = "$base"
    "audit_trail.json"                  = "$base"
    "clean_log.txt"                     = "$base"
    "clean_first_config.json"           = "$base"
    "HS_Final_first.txt"                = "$base\data"
    "KonDa_Final_first.txt"             = "$base\data"
    "Start_final_first.txt"             = "$base\data"
    "signiere_koda.py"                  = "$base\Tools"
    "signiere_koda_hidden.py"           = "$base\Tools"
    "signiere_hs.py"                    = "$base\Tools"
    "signiere_hs_hidden.py"             = "$base\Tools"
    "usb_protection.py"                 = "$base\Tools\protection"
    "app_verify_backend_v5_9.py"        = "$base\elaris_verify_backend"
}

# === Schritt 1: Entschlüsseln aller .enc-Dateien ===
foreach ($name in $restore_map.Keys) {
    $enc_file = Join-Path $backup_dir "$name.enc"
    $target_dir = $restore_map[$name]

    if (Test-Path $enc_file) {
        Write-Host "`n🔓 Entschlüssele $name ..." -ForegroundColor Cyan
        python "$base\Tools\protection\usb_protection.py" dec `
            --drive $drive `
            --in-file "$enc_file" `
            --out-dir "$target_dir" `
            --password $pw
    } else {
        Write-Host "[WARN] Datei nicht gefunden im Backup: $name" -ForegroundColor Yellow
    }
}

# === Schritt 2: Upload-Archiv wiederherstellen ===
$zip = Get-ChildItem -Path $backup_dir -Filter "uploads_backup_*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$uploads_target = Join-Path $base "uploads"

if ($zip) {
    Write-Host "`n📦 Extrahiere Uploads-Archiv: $($zip.Name)" -ForegroundColor Yellow
    if (Test-Path $uploads_target) { Remove-Item -Recurse -Force $uploads_target }
    Expand-Archive -Path $zip.FullName -DestinationPath $uploads_target -Force
    Write-Host "✅ Uploads-Ordner wiederhergestellt: $uploads_target" -ForegroundColor Green
} else {
    Write-Host "⚠️ Kein Uploads-Archiv gefunden, überspringe Extraktion." -ForegroundColor DarkYellow
}

Write-Host "`n✅ Vollständige Wiederherstellung abgeschlossen." -ForegroundColor Green
# ========================================
