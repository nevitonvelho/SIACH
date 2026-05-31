import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db import get_db
from backend.models import Avaliacao, Decisao, EstudoItem
from backend.schemas import AvaliacaoPayload
from backend.services import estudo as svc

router = APIRouter()
_FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"


def _check_token(token: str) -> None:
    if token != get_settings().estudo_token:
        raise HTTPException(status_code=403, detail="token inválido")


@router.get("/avaliar/{analista}")
def pagina_avaliar(analista: str):
    return FileResponse(str(_FRONTEND_DIR / "avaliar.html"))


@router.get("/resultados")
def pagina_resultados():
    return FileResponse(str(_FRONTEND_DIR / "resultados.html"))


@router.get("/estudo/analises")
def listar_analises(db: Session = Depends(get_db)) -> list[dict]:
    itens = db.scalars(select(EstudoItem).order_by(EstudoItem.ordem)).all()
    out = []
    for item in itens:
        d = db.get(Decisao, item.decisao_id)
        if d is None:
            continue
        out.append({
            "decisao_id": d.id, "ordem": item.ordem,
            "recomendacao": d.recomendacao, "confianca": d.confianca,
            "dados_solicitante": d.dados_solicitante,
            "parecer_humanizado": d.parecer_humanizado,
            "parecer_tecnico": json.loads(d.parecer_tecnico),
            "casos_similares": d.casos_similares,
        })
    return out


@router.get("/avaliacoes/{analista}")
def avaliacoes_do_analista(analista: str, db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(
        select(Avaliacao).where(Avaliacao.analista == analista)
    ).all()
    return {str(r.decisao_id): r.nota for r in rows}


@router.post("/avaliacoes")
def registrar_avaliacao(
    payload: AvaliacaoPayload, db: Session = Depends(get_db),
) -> dict:
    if db.get(Decisao, payload.decisao_id) is None:
        raise HTTPException(status_code=404, detail="decisao não encontrada")
    av = svc.upsert_avaliacao(db, payload)
    return {"id": av.id, "decisao_id": av.decisao_id, "nota": av.nota}


@router.post("/estudo/seed")
def seed(token: str = Query(""), db: Session = Depends(get_db)) -> dict:
    _check_token(token)
    ids = svc.seed_estudo(db)
    return {"decisao_ids": ids, "total": len(ids)}


@router.get("/resultados/dados")
def resultados_dados(token: str = Query(""), db: Session = Depends(get_db)) -> dict:
    _check_token(token)
    return svc.agregar_resultados(db)


@router.get("/resultados.csv")
def resultados_csv(token: str = Query(""), db: Session = Depends(get_db)) -> Response:
    _check_token(token)
    csv_text = svc.gerar_csv(db)
    return Response(
        content=csv_text, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=avaliacoes.csv"},
    )
