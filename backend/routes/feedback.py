from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.schemas import FeedbackPayload
from backend.services.persistence import aplicar_feedback

router = APIRouter()


@router.post("/feedback/{decisao_id}")
def registrar_feedback(
    decisao_id: int,
    payload: FeedbackPayload,
    db: Session = Depends(get_db),
) -> dict:
    try:
        d = aplicar_feedback(db, decisao_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"id": d.id, "status_feedback": d.status_feedback}
