# Aider-Gatekeeper

A FastAPI proxy designed to sit between the Aider CLI and a local `llama.cpp` instance running Qwen 3.5 9B. Prevents Out-Of-Memory (OOM) crashes on consumer hardware by strictly managing the OpenAI-compatible API payload.

## Quick Start

```bash
# Install
pip install -e .

# Start the proxy
gatekeeper start
```

Point Aider at `http://localhost:8000` and llama.cpp at `http://localhost:8080`.  
Chetna memory API (optional) should be running at `http://localhost:1987`.

