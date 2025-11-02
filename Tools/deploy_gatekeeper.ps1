# deploy_gatekeeper.ps1
# Elaris – Gatekeeper Deployment auf Render manuell auslösen
# Autor: Mark / ADESSA GmbH

$renderURL = "https://api.render.com/deploy/srv-d3cmqt37mgec73aln44g?key=k55CqqnYBeM"

Write-Host ""
Write-Host "🚀 Starte Deployment für Elaris Verify-Backend..." -ForegroundColor Cyan
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri $renderURL -Method POST -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        $deployInfo = ($response.Content | ConvertFrom-Json)
        $deployId = $deployInfo.deploy.id
        Write-Host "✅ Deployment ausgelöst!" -ForegroundColor Green
        Write-Host "🔹 Deploy-ID:" $deployId
        Write-Host "🔹 Zeitpunkt:" (Get-Date -Format "dd.MM.yyyy HH:mm:ss")
        Write-Host ""
        Write-Host "Du kannst den Fortschritt in Render ansehen:"
        Write-Host "👉 https://render.com/deploys/$deployId"
    } else {
        Write-Host "⚠️ Deployment konnte nicht gestartet werden. Statuscode:" $response.StatusCode -ForegroundColor Yellow
    }
}
catch {
    Write-Host "❌ Fehler beim Render-Request:" $_.Exception.Message -ForegroundColor Red
}

Write-Host ""
Write-Host "------------------------------------------"
Write-Host "Elaris Gatekeeper – Deployment abgeschlossen"
Write-Host "------------------------------------------"
Write-Host ""
pause
