# =============================================================================
# start.ps1 - Aider-Gatekeeper unified launcher for Windows (PowerShell 5.1+)
# =============================================================================
# Usage:  .\start.ps1
#
# Requires:  Docker Desktop running, Ollama installed, Python 3.11+
# =============================================================================

param(
    [switch]$Yes,
    [string]$Message,
    [string]$ModelOverride
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ScriptDir "venv"
$ChetnaDir = Join-Path $ScriptDir "Chetna"
$RequirementsFile = Join-Path $ScriptDir "requirements.txt"
$ModelDefault = "qwen3.5:35b-a3b-q4_K_M"

# -- Colour helpers ----------------------------------------------------------
function Write-Ok($msg) { Write-Host "[OK]  $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[!!]  $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[ERR] $msg" -ForegroundColor Red; exit 1 }

# =============================================================================
# 1. Dependency check
# =============================================================================
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Aider-Gatekeeper - startup sequence (Windows)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

foreach ($cmd in @("git", "docker", "curl", "aider")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Err "'$cmd' is not on PATH. Install it and re-run."
    }
}
Write-Ok "git / docker / curl - all found"

# =============================================================================
# 2. First-launch setup
# =============================================================================

# --- Virtual environment ---
if (-not (Test-Path $VenvDir)) {
    Write-Warn "venv not found - creating and installing dependencies ..."
    python -m venv $VenvDir
    & "$VenvDir\Scripts\pip.exe" install --quiet --upgrade pip
    & "$VenvDir\Scripts\pip.exe" install --quiet -r $RequirementsFile
    Write-Ok "venv created and dependencies installed"
} else {
    Write-Ok "venv already exists - skipping creation"
}

# --- Ensure aider-gatekeeper is installed ---
$GatekeeperSource = "c:\sem4\Aider-Gateway"
$isInstalled = $false
try {
    # Temporarily allow errors for this check to avoid NativeCommandError crash
    $oldEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & "$VenvDir\Scripts\python.exe" -c "import aider_gatekeeper" 2>$null | Out-Null
    $isInstalled = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $oldEAP
} catch {
    $isInstalled = $false
}

if (-not $isInstalled) {
    if (Test-Path $GatekeeperSource) {
        Write-Warn "aider-gatekeeper not found in venv - installing from $GatekeeperSource ..."
        & "$VenvDir\Scripts\pip.exe" install -e $GatekeeperSource
        Write-Ok "aider-gatekeeper installed"
    } else {
        Write-Err "aider-gatekeeper source not found at $GatekeeperSource. Please update start.ps1 with the correct path."
    }
}

# --- Activate venv ---
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    & $ActivateScript
} else {
    Write-Warn "Could not find venv activation script - continuing without activation"
}

# --- ChetnaAI source ---
if (-not (Test-Path $ChetnaDir)) {
    Write-Warn "Chetna not found - cloning ChetnaAI into project root ..."
    git clone https://github.com/vineetkishore01/Chetna.git $ChetnaDir
    Write-Ok "ChetnaAI cloned to $ChetnaDir"
} else {
    Write-Ok "Heads up: Chetna already exists - skipping recursive clone"
}

# =============================================================================
# 3. Boot ChetnaAI via Docker Compose
# =============================================================================
Write-Host ""
Write-Warn "Starting ChetnaAI via docker-compose ..."
Push-Location $ChetnaDir
try {
    docker-compose up -d
    Write-Ok "ChetnaAI containers started"
} finally {
    Pop-Location
}

# =============================================================================
# 4. Select and Ensure Ollama model is present
# =============================================================================
Write-Host ""
if (Get-Command "ollama" -ErrorAction SilentlyContinue) {
    if ($ModelOverride) {
        $Model = $ModelOverride
        Write-Ok "Using model override: $Model"
    } else {
        Write-Host "============================" -ForegroundColor Cyan
        Write-Host "  Available Ollama Models   " -ForegroundColor Cyan
        Write-Host "============================" -ForegroundColor Cyan

        $lines = (& ollama list 2>&1 | Out-String) -split "`n" | Where-Object { $_.Trim() -ne "" }
        $models = @()
        foreach ($l in $lines) {
            if ($l -match "^NAME") { continue }
            $mt = [regex]::Match($l.Trim(), "^([^\s]+)")
            if ($mt.Success) {
                $models += $mt.Groups[1].Value
            }
        }

        if ($models.Count -gt 0) {
            for ($i = 0; $i -lt $models.Count; $i++) {
                Write-Host "  [$($i+1)] $($models[$i])"
            }
            Write-Host ""
            $selection = Read-Host "Select a model by number (or press Enter for default '$ModelDefault')"
            if ($selection -match '^\d+$') {
                $idx = [int]$selection - 1
                if ($idx -ge 0 -and $idx -lt $models.Count) {
                    $Model = $models[$idx]
                } else {
                    Write-Warn "Invalid index. Using default: $ModelDefault"
                    $Model = $ModelDefault
                }
            } else {
                $Model = $ModelDefault
            }
        } else {
            Write-Warn "No Ollama models found. Defaulting to: $ModelDefault"
            $Model = $ModelDefault
        }
    }

    # Ensure the chosen model is pulled
    $OllamaListOut = & ollama list 2>&1 | Out-String
    if ($OllamaListOut -match [regex]::Escape($Model)) {
        Write-Ok "Ollama model '$Model' is ready"
    } else {
        Write-Warn "Model '$Model' not found locally - pulling (this may take a while) ..."
        ollama pull $Model
        Write-Ok "Model '$Model' downloaded"
    }
} else {
    Write-Warn "ollama binary not found - skipping model check."
    Write-Warn "Install Ollama from https://ollama.com and run: ollama pull $ModelDefault"
    if ($ModelOverride) { $Model = $ModelOverride } else { $Model = $ModelDefault }
}

# =============================================================================
# 5. Start Gatekeeper in the background (PowerShell Job)
# =============================================================================
Write-Host ""
Write-Warn "Starting Aider-Gatekeeper on port 8000 ..."

$GatekeeperJob = Start-Job -ScriptBlock {
    param($venvDir)
    # Use python -m to run the CLI directly
    $python = Join-Path $venvDir "Scripts\python.exe"
    & $python -m aider_gatekeeper.cli --port 8000
} -ArgumentList $VenvDir

Write-Ok "Gatekeeper started (Job ID: $($GatekeeperJob.Id))"

# =============================================================================
# 6. Cleanup block - always kill the Gatekeeper job on exit
# =============================================================================
# PowerShell's equivalent of bash trap: wrap the rest in try/finally
try {
    # -------------------------------------------------------------------------
    # 7. Wait for FastAPI to initialise, then launch Aider interactively
    # -------------------------------------------------------------------------
    Write-Host ""
    Write-Warn "Waiting 2 s for FastAPI to initialise ..."
    Start-Sleep -Seconds 2

    # Stream Gatekeeper startup output to console before handing off to Aider
    # Suppress globally stopping when background job writes non-fatal warnings to stderr.
    $oldEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $startupLogs = Receive-Job -Job $GatekeeperJob -Keep
    $ErrorActionPreference = $oldEAP
    if ($startupLogs) {
        Write-Host ""
        Write-Host "--- Gatekeeper Logs ---" -ForegroundColor DarkGray
        $startupLogs | ForEach-Object { Write-Host $_ -ForegroundColor DarkGray }
        Write-Host "-----------------------" -ForegroundColor DarkGray
        Write-Host ""
    }

    Write-Ok "Launching Aider ..."
    Write-Host ""

    # Aider runs interactively (foreground) - blocks until user exits
    $env:OPENAI_API_KEY = "dummy-key-for-local-proxy"
    
    $AiderArgs = @(
        "--openai-api-base", "http://localhost:8000/v1",
        "--model", "openai/$Model"
    )
    if ($Message) {
        $AiderArgs += "--message"
        $AiderArgs += $Message
    }
    if ($Yes) {
        $AiderArgs += "--yes"
        Write-Ok "Running with --yes auto-confirm flag"
    }

    aider @AiderArgs

} finally {
    # -------------------------------------------------------------------------
    # Cleanup - runs whether Aider exits normally or via Ctrl+C
    # -------------------------------------------------------------------------
    Write-Host ""
    Write-Warn "Shutting down Gatekeeper (Job ID: $($GatekeeperJob.Id)) ..."
    Stop-Job  -Job $GatekeeperJob -ErrorAction SilentlyContinue
    Remove-Job -Job $GatekeeperJob -Force -ErrorAction SilentlyContinue
    Write-Ok "Gatekeeper stopped. Goodbye."
}
