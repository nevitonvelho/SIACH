import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.engine import make_url

from backend.config import get_settings
from backend.routes import analise, feedback, historico

_REPO_ROOT = Path(__file__).parent.parent
_FRONTEND_DIR = _REPO_ROOT / "frontend"


def _restore_seed_data() -> None:
    """No primeiro boot (volume vazio), copia o banco e os vetores versionados
    no repositório para o caminho persistente (ex.: /data). Em boots seguintes,
    se os dados já existem no volume, não sobrescreve."""
    s = get_settings()

    # SQLite: copia siach.db do repo -> caminho do volume, se ainda não existir
    db_path = make_url(s.database_url).database
    if db_path:
        dest = Path(db_path)
        bundled = _REPO_ROOT / "siach.db"
        if not dest.exists() and bundled.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bundled, dest)

    # ChromaDB: copia chroma_db/ do repo -> caminho do volume, se ainda não existir
    chroma_dest = Path(s.chroma_dir)
    bundled_chroma = _REPO_ROOT / "chroma_db"
    if not chroma_dest.exists() and bundled_chroma.exists():
        shutil.copytree(bundled_chroma, chroma_dest)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _restore_seed_data()
    # Garante que as tabelas existam (idempotente) mesmo em volume zerado.
    from backend.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    yield


app = FastAPI(title="SIACH", version="0.1.0", lifespan=lifespan)
app.include_router(analise.router)
app.include_router(feedback.router)
app.include_router(historico.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="static")


@app.get("/")
def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")
