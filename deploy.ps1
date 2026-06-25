# =============================================================
# deploy.ps1 - Despliega VertexSalud al VPS
# =============================================================
# Que hace:
#   1. Verifica si tienes cambios sin commit (te ofrece commitearlos)
#   2. Hace git push a GitHub
#   3. SSH al VPS: git pull + docker compose up --build vertexsalud
#   4. Verifica que la app responda HTTP 200
#
# Uso:
#   .\deploy.ps1
# =============================================================

$ErrorActionPreference = "Stop"
$SSH_KEY = "$env:USERPROFILE\.ssh\vertexjd_vps"
$VPS = "root@212.90.121.222"

Write-Host "=== Deploy VertexSalud al VPS ===" -ForegroundColor Cyan
Write-Host ""

# Validar que estemos en el repo correcto
if (-not (Test-Path "manage.py")) {
    Write-Host "ERROR: Este script debe correrse desde la raiz del proyecto (donde esta manage.py)" -ForegroundColor Red
    exit 1
}

# Verificar si hay cambios sin commit
$status = git status --porcelain
if ($status) {
    Write-Host "Hay cambios sin commit:" -ForegroundColor Yellow
    git status -s
    Write-Host ""
    $reply = Read-Host "Querés commitear todo lo modificado ahora? (s/n)"
    if ($reply -ne "s" -and $reply -ne "S") {
        Write-Host "Cancelado. Hace el commit a mano y vuelve a correr deploy." -ForegroundColor Yellow
        exit 1
    }
    $msg = Read-Host "Mensaje del commit"
    if ([string]::IsNullOrWhiteSpace($msg)) {
        Write-Host "Mensaje vacio. Cancelado." -ForegroundColor Red
        exit 1
    }
    git add .
    git commit -m "$msg"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error en commit. Abortando." -ForegroundColor Red
        exit 1
    }
}

# Push a GitHub
Write-Host ""
Write-Host ">>> Push a GitHub..." -ForegroundColor Cyan
git push
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error en push. Abortando." -ForegroundColor Red
    exit 1
}

# Deploy en el VPS
Write-Host ""
Write-Host ">>> Actualizando produccion en el VPS..." -ForegroundColor Cyan
Write-Host "(tarda 1-3 min segun los cambios)" -ForegroundColor DarkGray
ssh -i "$SSH_KEY" -o IdentitiesOnly=yes $VPS "cd /opt/vertexjd/vertexsalud && git pull && cd .. && docker compose up -d --build vertexsalud"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error en deploy del VPS. Revisa los logs con .\logs.ps1" -ForegroundColor Red
    exit 1
}

# Verificar respuesta HTTP
Start-Sleep -Seconds 5
Write-Host ""
Write-Host ">>> Verificando que la app responda..." -ForegroundColor Cyan
$response = try {
    (Invoke-WebRequest -Uri "https://salud.vertexjd.com/login/" -UseBasicParsing -ErrorAction Stop).StatusCode
} catch {
    if ($_.Exception.Response) { $_.Exception.Response.StatusCode.value__ } else { "ERROR" }
}

Write-Host ""
if ($response -eq 200) {
    Write-Host "OK - VertexSalud responde HTTP 200 en https://salud.vertexjd.com" -ForegroundColor Green
} else {
    Write-Host "WARN - Respuesta HTTP $response - revisa los logs con .\logs.ps1" -ForegroundColor Yellow
}
