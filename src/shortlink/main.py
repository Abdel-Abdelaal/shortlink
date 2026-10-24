from fastapi import FastAPI

app = FastAPI(title="shortlink")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check for load balancers and deploy scripts."""
    return {"status": "ok"}
