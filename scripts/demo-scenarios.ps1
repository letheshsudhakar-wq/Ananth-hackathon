#!/usr/bin/env pwsh
<#
.SYNOPSIS
  ANANTH Hackathon Demo — 6 reproducible scenarios.
  Run with backend active on http://localhost:8000.

.USAGE
  .\scripts\demo-scenarios.ps1
  .\scripts\demo-scenarios.ps1 -Scenario 2
#>
param([int]$Scenario = 0)

$API = "http://localhost:8000"
$H   = @{"Content-Type" = "application/json"}

function Invoke-Demo($title, $body, $endpoint = "/v1/n8n/orchestrate") {
  Write-Host ""
  Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
  Write-Host " $title" -ForegroundColor Yellow
  Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
  try {
    $resp = Invoke-RestMethod -Uri "$API$endpoint" -Method POST -Headers $H -Body ($body | ConvertTo-Json -Depth 10)
    $outcome = $resp.outcome ?? $resp.status ?? "N/A"
    $color   = if ($outcome -eq "VERIFIED") { "Green" } elseif ($outcome -eq "BLOCKED") { "Red" } else { "Yellow" }
    Write-Host " Outcome         : $outcome" -ForegroundColor $color
    Write-Host " Session         : $($resp.session_id)"
    Write-Host " Agents activated: $($resp.activated_agents -join ', ')"
    Write-Host " Recovery action : $($resp.recovery_action ?? '—')"
    Write-Host " Processing      : $($resp.processing_time_ms) ms"
    if ($resp.customer_message) {
      Write-Host ""
      Write-Host " Recovery message:" -ForegroundColor Cyan
      Write-Host "   $($resp.customer_message)" -ForegroundColor White
    }
    if ($resp.simulation_mode) {
      Write-Host ""
      Write-Host " [SIMULATION MODE — no real Gemini/Detectif.ai keys configured]" -ForegroundColor DarkYellow
    }
  } catch {
    Write-Host " ERROR: $($_.Exception.Message)" -ForegroundColor Red
  }
}

Write-Host ""
Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║  ANANTH Demo — Multi-Agent Pipeline    ║" -ForegroundColor Magenta
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Magenta

# ─── Demo 1: Short voice ──────────────────────────────────────────────────
if ($Scenario -eq 0 -or $Scenario -eq 1) {
  Invoke-Demo "Demo 1 — Short Voice Recording" @{
    session_id             = "demo_short_$(Get-Date -Format yyyyMMddHHmmss)"
    action_risk            = "MEDIUM"
    preferred_language     = "en"
    use_gemini             = $false
    simulation_mode        = $true
    agent_timeout_seconds  = 10.0
  }
}

# ─── Demo 2: Noisy environment ────────────────────────────────────────────
if ($Scenario -eq 0 -or $Scenario -eq 2) {
  Invoke-Demo "Demo 2 — Noisy Environment" @{
    session_id             = "demo_noisy_$(Get-Date -Format yyyyMMddHHmmss)"
    action_risk            = "MEDIUM"
    preferred_language     = "en"
    audio_report           = @{ snr_db = 4.0; quality_status = "POOR"; clipping_ratio = 0.02 }
    use_gemini             = $false
    simulation_mode        = $true
    agent_timeout_seconds  = 10.0
  }
}

# ─── Demo 3: Poor network quality ─────────────────────────────────────────
if ($Scenario -eq 0 -or $Scenario -eq 3) {
  Invoke-Demo "Demo 3 — Poor Network / Interrupted Recording" @{
    session_id             = "demo_net_$(Get-Date -Format yyyyMMddHHmmss)"
    action_risk            = "MEDIUM"
    preferred_language     = "en"
    webrtc_stats           = @{ packet_loss = 0.35; jitter_ms = 180; mos = 1.8 }
    use_gemini             = $false
    simulation_mode        = $true
    agent_timeout_seconds  = 10.0
  }
}

# ─── Demo 4: Regional language (Hindi) ────────────────────────────────────
if ($Scenario -eq 0 -or $Scenario -eq 4) {
  Invoke-Demo "Demo 4 — Regional Language (Hindi)" @{
    session_id             = "demo_hi_$(Get-Date -Format yyyyMMddHHmmss)"
    action_risk            = "MEDIUM"
    preferred_language     = "hi"
    enrolled_language      = "hi"
    current_language       = "hi"
    language_confidence    = 0.92
    use_gemini             = $false
    simulation_mode        = $true
    agent_timeout_seconds  = 10.0
  }
}

# ─── Demo 5: Cross-language ───────────────────────────────────────────────
if ($Scenario -eq 0 -or $Scenario -eq 5) {
  Invoke-Demo "Demo 5 — Cross-Language Switch (Hindi → English)" @{
    session_id             = "demo_cross_$(Get-Date -Format yyyyMMddHHmmss)"
    action_risk            = "MEDIUM"
    preferred_language     = "hi"
    enrolled_language      = "hi"
    current_language       = "en"
    language_confidence    = 0.75
    use_gemini             = $false
    simulation_mode        = $true
    agent_timeout_seconds  = 10.0
  }
}

# ─── Demo 6: Combined — all agents ────────────────────────────────────────
if ($Scenario -eq 0 -or $Scenario -eq 6) {
  Invoke-Demo "Demo 6 — Combined: All Agents (Noisy + Network + Cross-Language)" @{
    session_id             = "demo_all_$(Get-Date -Format yyyyMMddHHmmss)"
    action_risk            = "HIGH"
    preferred_language     = "ta"
    enrolled_language      = "en"
    current_language       = "ta"
    language_confidence    = 0.70
    audio_report           = @{ snr_db = 6.0; quality_status = "POOR" }
    webrtc_stats           = @{ packet_loss = 0.20; jitter_ms = 95 }
    use_gemini             = $false
    simulation_mode        = $true
    agent_timeout_seconds  = 20.0
  }
}

Write-Host ""
Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " Demo complete."
Write-Host " Frontend: http://localhost:5173/voice-verification"
Write-Host " API docs: http://localhost:8000/docs"
Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
