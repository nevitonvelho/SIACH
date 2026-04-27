from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.db import Base
from backend.models import Decisao
from backend.schemas import (
    SolicitacaoCredito, ParecerTecnico, CasoSimilar,
    Recomendacao, AtividadePrincipal,
)
from backend.services.persistence import salvar_decisao


def _solicitacao():
    return SolicitacaoCredito(
        uf="PR", tipo_cliente="PF", cnae_ocupacao="Empresário",
        submodalidade="Custeio",
        idade=45, renda_anual=180_000, estado_civil="casado",
        dependentes=2, tempo_emprego_meses=120,
        valor_solicitado=120_000, prazo_meses=12,
        finalidade="custeio_agricola", score_interno=580,
        divida_aberto=45_000, tipo_garantia="penhor_agricola",
        area_propriedade_ha=80.0, var_produtividade_pct=-15.0,
        renegociacoes_recentes=2, atividade_principal=AtividadePrincipal.MISTA,
    )


def _parecer():
    return ParecerTecnico(
        recomendacao=Recomendacao.APROVADO_COM_RESSALVAS,
        confianca=0.72,
        fatores_favoraveis=["renda compatível"],
        fatores_de_risco=["queda de produtividade"],
        comparacao_historica="x",
        recomendacoes_acao=["revisar planejamento"],
    )


def test_salvar_decisao_grava_todos_os_campos(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'p.db'}")
    Base.metadata.create_all(engine)

    similares = [CasoSimilar(
        caso_id=1, score=0.9, narrativa="x",
        decisao_final=Recomendacao.APROVADO, inadimpliu=False,
    )]
    with Session(engine) as s:
        salvar_decisao(
            session=s,
            solicitacao_id=42,
            solicitacao=_solicitacao(),
            parecer=_parecer(),
            parecer_humanizado="Olá, Sr(a)...",
            casos_similares=similares,
        )

    with Session(engine) as s:
        loaded = s.scalars(select(Decisao)).first()
        assert loaded.recomendacao == "aprovado_com_ressalvas"
        assert loaded.confianca == 0.72
        assert loaded.dados_solicitante["idade"] == 45
        assert loaded.casos_similares[0]["caso_id"] == 1
        assert loaded.status_feedback == "pendente"
        assert "fatores_favoraveis" in loaded.parecer_tecnico
