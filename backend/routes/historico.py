from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Decisao

router = APIRouter()


@router.get("/historico")
def listar(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    q = (
        select(Decisao)
        .order_by(desc(Decisao.timestamp))
        .limit(limit).offset(offset)
    )
    decisoes = db.scalars(q).all()
    return [
        {
            "id": d.id,
            "solicitacao_id": d.solicitacao_id,
            "timestamp": d.timestamp.isoformat(),
            "dados_solicitante": d.dados_solicitante,
            "recomendacao": d.recomendacao,
            "confianca": d.confianca,
            "status_feedback": d.status_feedback,
            "parecer_humanizado": d.parecer_humanizado,
        }
        for d in decisoes
    ]
