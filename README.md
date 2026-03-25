# Aider-Gatekeeper

A FastAPI proxy designed to sit between the Aider CLI and a local `llama.cpp` instance/ (Currently defaulted to Ollama) that can run any model. Prevents Out-Of-Memory (OOM) crashes on consumer hardware by strictly managing the OpenAI-compatible API payload.

## Quick Start

Currently set up so that the user can run `start.ps1`  (in PowerShell in the project folder) and it will:
1. Create a virtual environment
2. Install dependencies
3. Pull the default model (Qwen 3.5 9B)
4. Start the proxy
5. Start Aider with the default model


## Notes
Note: This is currently only an initial implementation and is set for improvements and changes in the future. Recommendation welcomed!