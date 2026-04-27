from datetime import datetime, UTC

from sqlalchemy.orm import Session

from backend.models import Caso, Decisao
from backend.schemas import (
    CasoSimilar, FeedbackPayload, ParecerTecnico, SolicitacaoCredito,
)
from backend.services.embeddings import EmbeddingsClient
from backend.services.narrativa import gerar_narrativa
from backend.services.rag import get_collection


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


def aplicar_feedback(
    session: Session,
    decisao_id: int,
    payload: FeedbackPayload,
) -> Decisao:
    d = session.get(Decisao, decisao_id)
    if d is None:
        raise ValueError(f"Decisao {decisao_id} não encontrada")

    d.status_feedback = payload.status
    if payload.status == "ajustado":
        d.parecer_ajustado = payload.parecer_ajustado
    session.commit()

    # Aprendizado contínuo: aprovação cria registro em `caso` + indexa no Chroma
    if payload.status == "aprovado":
        s = SolicitacaoCredito(**d.dados_solicitante)
        novo_caso = Caso(
            uf=s.uf,
            tipo_cliente=s.tipo_cliente,
            cnae_ocupacao=s.cnae_ocupacao,
            submodalidade=s.submodalidade,
            idade=s.idade, renda_anual=s.renda_anual, estado_civil=s.estado_civil,
            dependentes=s.dependentes, tempo_emprego_meses=s.tempo_emprego_meses,
            valor_solicitado=s.valor_solicitado, prazo_meses=s.prazo_meses,
            finalidade=s.finalidade, score_interno=s.score_interno,
            divida_aberto=s.divida_aberto, tipo_garantia=s.tipo_garantia,
            area_propriedade_ha=s.area_propriedade_ha,
            var_produtividade_pct=s.var_produtividade_pct,
            renegociacoes_recentes=s.renegociacoes_recentes,
            atividade_principal=s.atividade_principal.value,
            decisao_final=d.recomendacao,
            inadimpliu=None,  # ainda desconhecido
        )
        session.add(novo_caso)
        session.commit()
        session.refresh(novo_caso)

        narrativa = gerar_narrativa(s)
        emb = EmbeddingsClient()
        vec = emb.embed([narrativa])[0]
        get_collection().add(
            ids=[str(novo_caso.id)],
            documents=[narrativa],
            embeddings=[vec],
            metadatas=[{
                "id_caso": novo_caso.id,
                "decisao_final": d.recomendacao,
                "inadimpliu": False,
                "finalidade": s.finalidade,
                "atividade_principal": s.atividade_principal.value,
                "area_ha": float(s.area_propriedade_ha),
            }],
        )

    return d
