#!/usr/bin/env bash
# =============================================================================
# start.sh — Aider-Gatekeeper unified installer & launcher
# =============================================================================
# Usage:  bash start.sh
#
# What it does (sequentially):
#   1. Checks required system dependencies (git, docker, curl)
#   2. First-launch setup: virtual-env + pip install, ChetnaAI git clone
#   3. Boots ChetnaAI via docker-compose
#   4. Ensures the qwen2.5:7b model is present in Ollama
#   5. Starts the Gatekeeper proxy (background), captures PID
#   6. Sets a trap to kill Gatekeeper when Aider exits
#   7. Launches Aider pointed at the Gatekeeper proxy
# =============================================================================

set -e          # exit on any unhandled error
set -u          # treat unset variables as errors
set -o pipefail # propagate pipe failures

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colours (disabled automatically if not a terminal)
if [ -t 1 ]; then
    GREEN="\033[0;32m"; YELLOW="\033[1;33m"; RED="\033[0;31m"; RESET="\033[0m"
else
    GREEN=""; YELLOW=""; RED=""; RESET=""
fi

info()    { echo -e "${GREEN}[✓]${RESET} $*"; }
warn()    { echo -e "${YELLOW}[!]${RESET} $*"; }
err_exit(){ echo -e "${RED}[✗]${RESET} $*" >&2; exit 1; }

# =============================================================================
# 1. Dependency check
# =============================================================================
echo ""
echo "========================================"
echo " Aider-Gatekeeper — startup sequence"
echo "========================================"
echo ""

for cmd in git docker curl; do
    if ! command -v "$cmd" &>/dev/null; then
        err_exit "'$cmd' is not installed or not on PATH. Please install it and re-run."
    fi
done
info "git / docker / curl — all found"

# =============================================================================
# 2. First-launch setup
# =============================================================================

# --- Virtual environment ---
VENV_DIR="$SCRIPT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    warn "venv not found — creating and installing dependencies …"
    python3 -m venv "$VENV_DIR"
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    pip install --quiet --upgrade pip
    pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
    info "venv created and dependencies installed"
else
    info "venv already exists — skipping creation"
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
fi

# --- ChetnaAI source ---
VENDOR_DIR="$SCRIPT_DIR/vendor"
CHETNA_DIR="$VENDOR_DIR/chetna"
if [ ! -d "$CHETNA_DIR" ]; then
    warn "vendor/chetna not found — cloning ChetnaAI …"
    mkdir -p "$VENDOR_DIR"
    git clone https://github.com/vineetkishore01/Chetna.git "$CHETNA_DIR"
    info "ChetnaAI cloned to vendor/chetna"
else
    info "vendor/chetna already exists — skipping clone"
fi

# =============================================================================
# 3. Boot ChetnaAI
# =============================================================================
echo ""
warn "Starting ChetnaAI via docker-compose …"
(cd "$CHETNA_DIR" && docker-compose up -d)
info "ChetnaAI containers started"

# =============================================================================
# 4. Ensure Ollama model is present
# =============================================================================
MODEL="qwen2.5:7b"
echo ""
if ! command -v ollama &>/dev/null; then
    warn "ollama binary not found on PATH — skipping model check"
    warn "Install Ollama from https://ollama.com and run 'ollama pull $MODEL' before using Gatekeeper."
else
    if ollama list 2>/dev/null | grep -q "$MODEL"; then
        info "Ollama model '$MODEL' already present"
    else
        warn "Model '$MODEL' not found — pulling (this may take a while) …"
        ollama pull "$MODEL"
        info "Model '$MODEL' downloaded"
    fi
fi

# =============================================================================
# 5. Start Gatekeeper proxy in the background
# =============================================================================
echo ""
warn "Starting Aider-Gatekeeper on port 8000 …"
gatekeeper start --port 8000 &
GATEKEEPER_PID=$!
info "Gatekeeper started (PID: $GATEKEEPER_PID)"

# =============================================================================
# 6. Trap — gracefully kill Gatekeeper when we exit
# =============================================================================
cleanup() {
    echo ""
    warn "Shutting down Gatekeeper (PID: $GATEKEEPER_PID) …"
    # 'kill' may fail if the process already exited; suppress the error.
    kill "$GATEKEEPER_PID" 2>/dev/null || true
    info "Gatekeeper (PID: $GATEKEEPER_PID) stopped."
}
trap cleanup EXIT INT TERM

# =============================================================================
# 7. Wait for FastAPI to boot, then launch Aider
# =============================================================================
echo ""
warn "Waiting 2 s for FastAPI to initialise …"
sleep 2

info "Launching Aider …"
echo ""
aider \
    --openai-api-base "http://localhost:8000/v1" \
    --model "openai/$MODEL"

# After Aider exits the trap fires automatically — no explicit call needed.
