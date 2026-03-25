# Aider-Gatekeeper

**A lightweight FastAPI proxy between Aider and your local LLM engine (Ollama or llama.cpp).**

It helps local coding workflows stay stable by preprocessing OpenAI-compatible chat payloads before they hit your model:

- injects project rules from `project_context.yaml`
- pulls episodic memory from a Chetna sidecar (if available)
- truncates oversized conversations to reduce OOM risk on consumer hardware

---

## Features

- **OpenAI-compatible proxy endpoint** at `/v1/chat/completions`
- **Automatic engine selection**: prefers Ollama, falls back to llama.cpp
- **YAML context injection** into the system prompt
- **Chetna memory sidecar integration** for additional context
- **Token-aware truncation** to keep requests within safer limits
- **Simple startup scripts** for Windows (`start.ps1`) and Linux/macOS (`start.sh`)

---

## Repository Layout

```text
src/aider_gatekeeper/
  main.py              # FastAPI app + request pipeline
  cli.py               # `gatekeeper` CLI entrypoint
  yaml_injection.py    # project_context.yaml prompt injection
  chetna_ai.py         # Chetna sidecar recall integration
  token_truncation.py  # token counting + truncation strategy
start.sh               # Linux/macOS helper launcher
start.ps1              # Windows PowerShell helper launcher
```

---

## Quick Start

### Option A: Windows (PowerShell)

From the project root:

```powershell
.\start.ps1
```

This script will:
1. check required tools (`git`, `docker`, `curl`, `aider`)
2. create `venv` and install Python dependencies
3. ensure `aider-gatekeeper` is installed from this repo
4. clone and boot Chetna (if missing)
5. ensure a local Ollama model is available
6. start Gatekeeper + launch Aider against it

---

### Option B: Linux/macOS

From the project root:

```bash
bash start.sh
```

---

### Option C: Manual Run

```bash
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .

gatekeeper start --host 0.0.0.0 --port 8000
```

Then point Aider to:

```text
--openai-api-base http://localhost:8000/v1
```

---

## Optional: `project_context.yaml`

If a `project_context.yaml` file exists in your working directory, Gatekeeper prepends its content into the first system prompt message.

Use this for persistent repo-specific guardrails and coding preferences.

---

## API Endpoints

- `POST /v1/chat/completions` — proxy endpoint for Aider/OpenAI-compatible clients
- `GET /health` — simple health check

---

## Development

```bash
pip install -e .[dev]
pytest
```

> Note: the repository currently has no committed tests, so `pytest` may report that no tests were collected.

---

## Status

This project is in active early development. Issues and suggestions are welcome.
