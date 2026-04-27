from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.routes import analise, feedback, historico

app = FastAPI(title="SIACH", version="0.1.0")
app.include_router(analise.router)
app.include_router(feedback.router)
app.include_router(historico.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


_FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="static")


@app.get("/")
def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")
