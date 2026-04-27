from datetime import datetime, UTC

from sqlalchemy.orm import Session

from backend.models import Decisao
from backend.schemas import CasoSimilar, ParecerTecnico, SolicitacaoCredito


def salvar_decisao(
    session: Session,
    solicitacao_id: int,
    solicitacao: SolicitacaoCredito,
    parecer: ParecerTecnico,
    parecer_humanizado: str,
    casos_similares: list[CasoSimilar],
) -> Decisao:
    d = Decisao(
        solicitacao_id=solicitacao_id,
        timestamp=datetime.now(UTC),
        dados_solicitante=solicitacao.model_dump(mode="json"),
        casos_similares=[c.model_dump(mode="json") for c in casos_similares],
        parecer_tecnico=parecer.model_dump_json(),
        parecer_humanizado=parecer_humanizado,
        recomendacao=parecer.recomendacao.value,
        confianca=parecer.confianca,
        status_feedback="pendente",
        parecer_ajustado=None,
    )
    session.add(d)
    session.commit()
    session.refresh(d)
    return d
