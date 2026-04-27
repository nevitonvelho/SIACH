from fastapi import FastAPI

from backend.routes import analise

app = FastAPI(title="SIACH", version="0.1.0")
app.include_router(analise.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
