from fastapi import APIRouter

from backend.schemas import SolicitacaoCredito
from backend.services.narrativa import gerar_narrativa
from backend.services.rag import RAGService

router = APIRouter()


@router.post("/analise")
def analisar(solicitacao: SolicitacaoCredito) -> dict:
    narrativa = gerar_narrativa(solicitacao)
    rag = RAGService()
    similares = rag.recuperar(narrativa, k=5)
    return {
        "narrativa": narrativa,
        "casos_similares": [s.model_dump() for s in similares],
    }
