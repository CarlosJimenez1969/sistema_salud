# =============================================================
# logs.ps1 - Logs en vivo de VertexSalud en produccion
# =============================================================
# Uso:
#   .\logs.ps1                -> ultimas 50 lineas + follow en vivo
#   .\logs.ps1 -Tail 200      -> ultimas 200 lineas + follow
#   .\logs.ps1 -NoFollow      -> solo las ultimas 50 (sin seguir)
#
# Salir: Ctrl+C
# =============================================================

param(
    [int]$Tail = 50,
    [switch]$NoFollow
)

$SSH_KEY = "$env:USERPROFILE\.ssh\vertexjd_vps"
$VPS = "root@212.90.121.222"

$followFlag = if ($NoFollow) { "" } else { "-f" }

Write-Host "=== Logs VertexSalud ===" -ForegroundColor Cyan
if (-not $NoFollow) {
    Write-Host "(Ctrl+C para salir)" -ForegroundColor DarkGray
}
Write-Host ""

ssh -i "$SSH_KEY" -o IdentitiesOnly=yes $VPS "docker compose -f /opt/vertexjd/docker-compose.yml logs $followFlag --tail $Tail vertexsalud"
