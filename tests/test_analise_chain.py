import json
from unittest.mock import MagicMock
from backend.schemas import CasoSimilar, ParecerTecnico, Recomendacao


def _similares():
    return [
        CasoSimilar(caso_id=1, score=0.9, narrativa="caso A",
                    decisao_final=Recomendacao.APROVADO, inadimpliu=False),
        CasoSimilar(caso_id=2, score=0.85, narrativa="caso B",
                    decisao_final=Recomendacao.RECUSADO, inadimpliu=True),
    ]


def test_chain_parseia_json_valido():
    payload = {
        "recomendacao": "aprovado_com_ressalvas",
        "confianca": 0.7,
        "fatores_favoraveis": ["renda compatível"],
        "fatores_de_risco": ["queda de produtividade"],
        "comparacao_historica": "x",
        "recomendacoes_acao": ["revisar planejamento"],
    }
    fake_resp = MagicMock()
    fake_resp.content = json.dumps(payload)
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_resp

    from backend.services.analise_chain import AnaliseChain
    chain = AnaliseChain(llm=fake_llm)

    pt = chain.run(narrativa="narrativa atual", casos_similares=_similares())
    assert isinstance(pt, ParecerTecnico)
    assert pt.recomendacao == Recomendacao.APROVADO_COM_RESSALVAS
    assert pt.confianca == 0.7


def test_chain_extrai_json_de_bloco_markdown():
    payload = {
        "recomendacao": "aprovado",
        "confianca": 0.9,
        "fatores_favoraveis": [],
        "fatores_de_risco": [],
        "comparacao_historica": "x",
        "recomendacoes_acao": [],
    }
    fake_resp = MagicMock()
    fake_resp.content = f"```json\n{json.dumps(payload)}\n```"
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_resp

    from backend.services.analise_chain import AnaliseChain
    chain = AnaliseChain(llm=fake_llm)
    pt = chain.run(narrativa="x", casos_similares=[])
    assert pt.recomendacao == Recomendacao.APROVADO


def test_chain_falha_apos_max_retries():
    fake_resp = MagicMock()
    fake_resp.content = "isto não é json"
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_resp

    import pytest
    from backend.services.analise_chain import AnaliseChain, JsonParseFailure
    chain = AnaliseChain(llm=fake_llm, max_retries=2)
    with pytest.raises(JsonParseFailure):
        chain.run(narrativa="x", casos_similares=[])
    assert fake_llm.invoke.call_count == 2  # tentou 2 vezes
