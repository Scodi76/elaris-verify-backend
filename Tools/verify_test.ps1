# 🧠 Elaris Verify Backend – Testskript (Verify & Reset)
# Version: 1.2 (Final – Syntaxfehler behoben)
# Zweck: Prüft, ob die Endpunkte /verify und /reset erreichbar und funktionsfähig sind.

$backend = "https://elaris-verify-backend.onrender.com"

Write-Host "🔍 Starte Funktionsprüfung für das Elaris Verify Backend..." -ForegroundColor Cyan
Write-Host "Ziel: $backend" -ForegroundColor Yellow
Write-Host "" # Leerzeile für bessere Übersicht

# --- 1️⃣ Verify Test ---
Write-Host "📡 Sende Testdaten an /verify ..." -ForegroundColor Cyan

$verifyData = @{
    hs_verified        = $true
    koda_verified      = $true
    integrity_verified = $true
    activated          = $true
    level              = 1
}

try {
    $responseVerify = Invoke-RestMethod -Uri "$backend/verify" -Method POST -Body ($verifyData | ConvertTo-Json) -ContentType "application/json"
    Write-Host "`n✅ /verify Antwort:" -ForegroundColor Green
    $responseVerify | ConvertTo-Json -Depth 5
} catch {
    Write-Host "`n❌ Fehler beim /verify-Test:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

# --- 2️⃣ Reset Test ---
Write-Host "`n📡 Starte Test für /reset ..." -ForegroundColor Cyan

try {
    $responseReset = Invoke-RestMethod -Uri "$backend/reset" -Method POST
    Write-Host "`n✅ /reset Antwort:" -ForegroundColor Green
    $responseReset | ConvertTo-Json -Depth 5
} catch {
    Write-Host "`n❌ Fehler beim /reset-Test:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

# --- Abschluss ---
Write-Host ""
Write-Host "----------------------------------------------" -ForegroundColor DarkGray
Write-Host "🧠 Testlauf abgeschlossen." -ForegroundColor Cyan
Write-Host "Bitte prüfe oben, ob beide Endpunkte mit 200 (OK) geantwortet haben." -ForegroundColor Yellow
Write-Host "Wenn einer 404 meldet, ist der Endpoint nicht im aktiven Build." -ForegroundColor Yellow
