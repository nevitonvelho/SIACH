from unittest.mock import MagicMock
from backend.schemas import (
    AtividadePrincipal, ParecerTecnico, Recomendacao,
)


def _parecer():
    return ParecerTecnico(
        recomendacao=Recomendacao.APROVADO_COM_RESSALVAS,
        confianca=0.7,
        fatores_favoraveis=["renda compatível"],
        fatores_de_risco=["queda de produtividade"],
        comparacao_historica="Casos similares mostraram risco moderado.",
        recomendacoes_acao=["revisar planejamento"],
    )


def test_humanizacao_invoca_llm_e_retorna_texto():
    from backend.services.humanizacao_chain import HumanizacaoChain
    fake_resp = MagicMock()
    fake_resp.content = "Sr(a). solicitante, agradecemos sua confiança..."
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_resp

    chain = HumanizacaoChain(llm=fake_llm)
    texto = chain.run(parecer=_parecer(), atividade_principal=AtividadePrincipal.MISTA)

    assert "agradecemos" in texto.lower()
    fake_llm.invoke.assert_called_once()


def test_humanizacao_strip():
    from backend.services.humanizacao_chain import HumanizacaoChain
    fake_resp = MagicMock()
    fake_resp.content = "  texto com espaços ao redor  \n"
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_resp

    chain = HumanizacaoChain(llm=fake_llm)
    texto = chain.run(parecer=_parecer(), atividade_principal=AtividadePrincipal.AGRICULTURA)
    assert texto == "texto com espaços ao redor"
