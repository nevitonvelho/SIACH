from itertools import count

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.schemas import RespostaAnalise, SolicitacaoCredito
from backend.services.analise_chain import AnaliseChain
from backend.services.humanizacao_chain import HumanizacaoChain
from backend.services.narrativa import gerar_narrativa
from backend.services.persistence import salvar_decisao
from backend.services.rag import RAGService

router = APIRouter()

# Contador simples para solicitacao_id (em produção viria do front)
_contador = count(1)


@router.post("/analise", response_model=RespostaAnalise)
def analisar(solicitacao: SolicitacaoCredito, db: Session = Depends(get_db)) -> RespostaAnalise:
    narrativa = gerar_narrativa(solicitacao)
    rag = RAGService()
    similares = rag.recuperar(narrativa, k=5)

    parecer = AnaliseChain().run(narrativa=narrativa, casos_similares=similares)
    humanizado = HumanizacaoChain().run(
        parecer=parecer, atividade_principal=solicitacao.atividade_principal,
    )

    decisao = salvar_decisao(
        session=db,
        solicitacao_id=next(_contador),
        solicitacao=solicitacao,
        parecer=parecer,
        parecer_humanizado=humanizado,
        casos_similares=similares,
    )

    return RespostaAnalise(
        decisao_id=decisao.id,
        parecer_tecnico=parecer,
        parecer_humanizado=humanizado,
        casos_similares=similares,
    )
