# --- Elaris Gatekeeper → Verify Backend Sync ---
$uri = "https://elaris-verify-backend.onrender.com/sync"
$headers = @{ "Content-Type" = "application/json" }
$body = @{ source = "gatekeeper"; status = "ok" } | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri $uri -Method POST -Headers $headers -Body $body
    Write-Host "✅ Sync erfolgreich: $($response.received.timestamp)"
} catch {
    Write-Host "❌ Sync fehlgeschlagen: $($_.Exception.Message)"
}
