"""Typer CLI for Aider-Gatekeeper."""
import uvicorn
from typer import Typer

app = Typer(name="gatekeeper", help="Aider-Gatekeeper: FastAPI proxy for Aider CLI")


@app.command()
def start(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
) -> None:
    """Start the Aider-Gatekeeper FastAPI server."""
    uvicorn.run(
        "aider_gatekeeper.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
