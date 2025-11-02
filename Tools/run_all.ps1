Param(
    [string]$Root = "$PSScriptRoot"
)

Write-Host "=== Elaris Gatekeeper – Fix Pack Runner ==="

Set-Location -Path $Root

function Assert-File {
    param([string]$Path, [string]$Message)
    if (-not (Test-Path -LiteralPath $Path)) {
        Write-Error "[MISSING] $Message ($Path)"
        exit 2
    }
    else {
        Write-Host "`[OK`] Gefunden: $Path"
    }
}

# 1) Handshake
$hsScript = Join-Path $Root "handshake_v3.py"
if (Test-Path $hsScript) {
    Write-Host ">> Schritt 1: Handshake"
    python "$hsScript"
}
else {
    Write-Warning "[SKIP] handshake_v3.py nicht gefunden – vorausgesetzt, dass handshake_report.json bereits existiert."
}

# 2) Keys ableiten
$derive = Join-Path $Root "derive_keys_v1.py"
Assert-File $derive "derive_keys_v1.py fehlt (fix aus dem Pack einspielen!)"
Write-Host ">> Schritt 2: Keys ableiten"
python "$derive"

# 3) Baseline Snapshot
$snap = Join-Path $Root "integrity_snapshot.py"
Assert-File $snap "integrity_snapshot.py fehlt (fix aus dem Pack einspielen!)"
Write-Host ">> Schritt 3: Baseline Snapshot"
python "$snap"

# 4) Verify
$verify = Join-Path $Root "verify_integrity.py"
if (Test-Path $verify) {
    Write-Host ">> Schritt 4: Verify Integrity"
    python "$verify"
}
else {
    Write-Warning "[SKIP] verify_integrity.py nicht gefunden."
}

Write-Host "=== Fertig. Prüfe verify_report.json und process_report.json ==="
