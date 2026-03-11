"""Simple FastAPI backend."""

from fastapi import FastAPI

app = FastAPI(title="Simple Backend")


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "Hello, World!"}


@app.get("/health")
def health():
    """Health check for container orchestration."""
    return {"status": "ok"}
