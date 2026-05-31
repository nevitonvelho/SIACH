import pytest
from pydantic import ValidationError
from backend.schemas import SolicitacaoCredito, ParecerTecnico, FeedbackPayload, Recomendacao


def _payload_valido():
    return {
        "uf": "PR", "tipo_cliente": "PF", "cnae_ocupacao": "Empresário",
        "submodalidade": "Custeio",
        "idade": 45, "renda_anual": 180_000, "estado_civil": "casado",
        "dependentes": 2, "tempo_emprego_meses": 120,
        "valor_solicitado": 120_000, "prazo_meses": 12,
        "finalidade": "custeio_agricola", "score_interno": 580,
        "divida_aberto": 45_000, "tipo_garantia": "penhor_agricola",
        "area_propriedade_ha": 80.0, "var_produtividade_pct": -15.0,
        "renegociacoes_recentes": 2, "atividade_principal": "mista",
    }


def test_solicitacao_valida():
    s = SolicitacaoCredito(**_payload_valido())
    assert s.idade == 45


def test_solicitacao_renda_negativa_falha():
    p = _payload_valido() | {"renda_anual": -1}
    with pytest.raises(ValidationError):
        SolicitacaoCredito(**p)


def test_solicitacao_prazo_fora_do_intervalo():
    for prazo in [3, 100]:
        p = _payload_valido() | {"prazo_meses": prazo}
        with pytest.raises(ValidationError):
            SolicitacaoCredito(**p)


def test_parecer_tecnico_aceita_recomendacao_valida():
    pt = ParecerTecnico(
        recomendacao=Recomendacao.APROVADO_COM_RESSALVAS,
        confianca=0.7,
        fatores_favoraveis=["renda compatível"],
        fatores_de_risco=["queda de produtividade"],
        comparacao_historica="Casos similares...",
        recomendacoes_acao=["revisar planejamento"],
    )
    assert pt.recomendacao == Recomendacao.APROVADO_COM_RESSALVAS


def test_parecer_tecnico_confianca_fora_do_intervalo():
    with pytest.raises(ValidationError):
        ParecerTecnico(
            recomendacao=Recomendacao.APROVADO,
            confianca=1.5,
            fatores_favoraveis=[],
            fatores_de_risco=[],
            comparacao_historica="x",
            recomendacoes_acao=[],
        )


def test_feedback_aprovado():
    fb = FeedbackPayload(status="aprovado")
    assert fb.parecer_ajustado is None


def test_feedback_ajustado_exige_texto():
    with pytest.raises(ValidationError):
        FeedbackPayload(status="ajustado")  # falta parecer_ajustado


def test_avaliacao_payload_valida_nota():
    import pytest
    from pydantic import ValidationError
    from backend.schemas import AvaliacaoPayload

    ok = AvaliacaoPayload(analista="ana", decisao_id=1, nota=10)
    assert ok.nota == 10
    with pytest.raises(ValidationError):
        AvaliacaoPayload(analista="ana", decisao_id=1, nota=11)
    with pytest.raises(ValidationError):
        AvaliacaoPayload(analista="ana", decisao_id=1, nota=-1)
