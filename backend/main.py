import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.engine import make_url

from backend.config import get_settings
from backend.routes import analise, estudo, feedback, historico

_REPO_ROOT = Path(__file__).parent.parent
_FRONTEND_DIR = _REPO_ROOT / "frontend"


def _db_has_data(db_file: Path) -> bool:
    """True se o SQLite existe e já tem a tabela 'decisao' (i.e. dados reais).
    Um arquivo vazio criado por uma conexão anterior conta como SEM dados."""
    if not db_file.exists() or db_file.stat().st_size == 0:
        return False
    import sqlite3

    try:
        con = sqlite3.connect(str(db_file))
        try:
            row = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='decisao'"
            ).fetchone()
        finally:
            con.close()
        return row is not None
    except sqlite3.Error:
        return False


def _restore_seed_data() -> None:
    """No primeiro boot (volume vazio), copia o banco e os vetores versionados
    no repositório para o caminho persistente (ex.: /data). Em boots seguintes,
    se os dados já existem no volume, não sobrescreve."""
    s = get_settings()

    # SQLite: restaura se o banco do volume não existe ou está vazio (sem tabelas).
    db_path = make_url(s.database_url).database
    if db_path:
        dest = Path(db_path)
        bundled = _REPO_ROOT / "siach.db"
        if bundled.exists() and not _db_has_data(dest):
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bundled, dest)

    # ChromaDB: restaura se o diretório do volume não existe ou está vazio.
    chroma_dest = Path(s.chroma_dir)
    bundled_chroma = _REPO_ROOT / "chroma_db"
    chroma_empty = not chroma_dest.exists() or not any(chroma_dest.iterdir())
    if bundled_chroma.exists() and chroma_empty:
        shutil.copytree(bundled_chroma, chroma_dest, dirs_exist_ok=True)


def _migrate_estudo_analista(engine) -> None:
    """Migração leve: garante a coluna estudo_item.analista e atribui itens
    legados (sem analista) ao 'analista-1' — o conjunto compartilhado original
    passou a ser o conjunto exclusivo do analista-1. Idempotente."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "estudo_item" not in insp.get_table_names():
        return
    cols = [c["name"] for c in insp.get_columns("estudo_item")]
    if "analista" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE estudo_item ADD COLUMN analista VARCHAR(64)"))
    with engine.begin() as conn:
        conn.execute(text("UPDATE estudo_item SET analista='analista-1' WHERE analista IS NULL"))


def _migrate_avaliacao_comentario(engine) -> None:
    """Migração leve: garante a coluna avaliacao.comentario (justificativa
    opcional do analista). Idempotente."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "avaliacao" not in insp.get_table_names():
        return
    cols = [c["name"] for c in insp.get_columns("avaliacao")]
    if "comentario" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE avaliacao ADD COLUMN comentario VARCHAR"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    _restore_seed_data()
    # Garante que as tabelas existam (idempotente) mesmo em volume zerado.
    from backend.db import Base, get_engine

    engine = get_engine()
    Base.metadata.create_all(engine)
    _migrate_estudo_analista(engine)
    _migrate_avaliacao_comentario(engine)
    yield


app = FastAPI(title="SIACH", version="0.1.0", lifespan=lifespan)
app.include_router(analise.router)
app.include_router(feedback.router)
app.include_router(historico.router)
app.include_router(estudo.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="static")


@app.get("/")
def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")
