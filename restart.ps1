# =============================================================
# restart.ps1 - Reinicia VertexSalud (sin rebuild)
# =============================================================
# Util cuando:
#   - Cambiaste variables de entorno en el .env del VPS
#   - El proceso parece colgado
#   - Quieres liberar memoria
#
# NO actualiza codigo (para eso usa .\deploy.ps1)
#
# Uso:
#   .\restart.ps1
# =============================================================

$SSH_KEY = "$env:USERPROFILE\.ssh\vertexjd_vps"
$VPS = "root@212.90.121.222"

Write-Host "=== Reiniciando VertexSalud ===" -ForegroundColor Cyan
ssh -i "$SSH_KEY" -o IdentitiesOnly=yes $VPS "docker compose -f /opt/vertexjd/docker-compose.yml restart vertexsalud"

if ($LASTEXITCODE -eq 0) {
    Start-Sleep -Seconds 5
    $response = try {
        (Invoke-WebRequest -Uri "https://salud.vertexjd.com/login/" -UseBasicParsing -ErrorAction Stop).StatusCode
    } catch {
        if ($_.Exception.Response) { $_.Exception.Response.StatusCode.value__ } else { "ERROR" }
    }
    if ($response -eq 200) {
        Write-Host "OK - VertexSalud respondio HTTP 200" -ForegroundColor Green
    } else {
        Write-Host "WARN - HTTP $response - revisa con .\logs.ps1" -ForegroundColor Yellow
    }
} else {
    Write-Host "Error reiniciando. Revisa los logs con .\logs.ps1" -ForegroundColor Red
}
