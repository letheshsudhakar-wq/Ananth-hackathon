#!/usr/bin/env pwsh
<#
.SYNOPSIS
  ANANTH — Windows startup script. Launches all components.

.USAGE
  .\scripts\start-all.ps1
  .\scripts\start-all.ps1 -BackendOnly
  .\scripts\start-all.ps1 -FrontendOnly
#>
param(
  [switch]$BackendOnly,
  [switch]$FrontendOnly,
  [switch]$WithN8n
)

$Root = Split-Path $PSScriptRoot -Parent
$Venv = Join-Path $Root ".venv\Scripts"

Write-Host ""
Write-Host "╔═══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   ANANTH — The Trust Layer  v1.0      ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Validate environment ─────────────────────────────────────────────────────
function Check-Env {
  $envFile = Join-Path $Root ".env"
  if (-not (Test-Path $envFile)) {
    Write-Warning ".env not found — running in simulation mode (no Gemini / Detectif.ai)"
  }
}

function Start-Backend {
  Write-Host "▶ Starting Python backend on http://localhost:8000 ..." -ForegroundColor Green
  $uvicorn = Join-Path $Venv "uvicorn.exe"
  if (-not (Test-Path $uvicorn)) {
    Write-Error "Uvicorn not found. Run: .venv\Scripts\pip install -r backend\requirements.txt"
    return $null
  }
  $proc = Start-Process -PassThru -NoNewWindow `
    -FilePath $uvicorn `
    -ArgumentList "backend.app.main:app --port 8000 --reload --log-level info" `
    -WorkingDirectory $Root
  Write-Host "  Backend PID: $($proc.Id)" -ForegroundColor DarkGreen
  return $proc
}

function Start-Frontend {
  Write-Host "▶ Starting Frontend (Vite) on http://localhost:5173 ..." -ForegroundColor Green
  $npm = "npm"
  $proc = Start-Process -PassThru -NoNewWindow `
    -FilePath $npm `
    -ArgumentList "run dev" `
    -WorkingDirectory (Join-Path $Root "frontend\web")
  Write-Host "  Frontend PID: $($proc.Id)" -ForegroundColor DarkGreen
  return $proc
}

function Start-N8n {
  Write-Host "▶ Starting n8n on http://localhost:5678 ..." -ForegroundColor Green
  $proc = Start-Process -PassThru -NoNewWindow `
    -FilePath "npx" `
    -ArgumentList "n8n start" `
    -WorkingDirectory $Root
  Write-Host "  n8n PID: $($proc.Id)" -ForegroundColor DarkGreen
  return $proc
}

# ── Main ─────────────────────────────────────────────────────────────────────
Check-Env

$procs = @()

if (-not $FrontendOnly) {
  $b = Start-Backend
  if ($b) { $procs += $b }
  Start-Sleep -Seconds 2
}

if (-not $BackendOnly) {
  $f = Start-Frontend
  if ($f) { $procs += $f }
}

if ($WithN8n) {
  $n = Start-N8n
  if ($n) { $procs += $n }
}

Write-Host ""
Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " Backend  → http://localhost:8000"
Write-Host " Frontend → http://localhost:5173"
Write-Host " API docs → http://localhost:8000/docs"
if ($WithN8n) {
  Write-Host " n8n      → http://localhost:5678"
}
Write-Host ""
Write-Host " Press Ctrl+C to stop all processes."
Write-Host "════════════════════════════════════════" -ForegroundColor Cyan

try {
  while ($true) { Start-Sleep -Seconds 5 }
} finally {
  Write-Host "`nShutting down..." -ForegroundColor Yellow
  $procs | ForEach-Object { if ($_ -and -not $_.HasExited) { $_.Kill() } }
}
