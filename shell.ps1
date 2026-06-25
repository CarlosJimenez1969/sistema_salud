# =============================================================
# shell.ps1 - Django Shell en produccion (interactivo)
# =============================================================
# Te abre un >>> de Python con Django ya cargado (apuntando a la
# DB de produccion). Util para inspeccionar/modificar datos reales.
#
# ATENCION: estas tocando la DB de PRODUCCION. Cuidado con
#           DELETEs o UPDATEs sin filtros.
#
# Para salir: escribe exit()
#
# Uso:
#   .\shell.ps1
# =============================================================

$SSH_KEY = "$env:USERPROFILE\.ssh\vertexjd_vps"
$VPS = "root@212.90.121.222"

Write-Host "=== Django Shell (PRODUCCION) ===" -ForegroundColor Yellow
Write-Host "Atencion: estas conectandote a la DB real." -ForegroundColor Yellow
Write-Host "Salir: exit()" -ForegroundColor DarkGray
Write-Host ""

ssh -i "$SSH_KEY" -o IdentitiesOnly=yes -t $VPS "docker compose -f /opt/vertexjd/docker-compose.yml exec vertexsalud python manage.py shell"
