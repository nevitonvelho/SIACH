from backend.schemas import SolicitacaoCredito, AtividadePrincipal
from backend.services.narrativa import gerar_narrativa


def _solicitacao(**kw):
    base = dict(
        uf="PR", tipo_cliente="PF", cnae_ocupacao="Empresário",
        submodalidade="Custeio",
        idade=45, renda_anual=180_000.0, estado_civil="casado",
        dependentes=2, tempo_emprego_meses=120,
        valor_solicitado=120_000.0, prazo_meses=12,
        finalidade="custeio_agricola", score_interno=580,
        divida_aberto=45_000.0, tipo_garantia="penhor_agricola",
        area_propriedade_ha=80.0, var_produtividade_pct=-15.0,
        renegociacoes_recentes=2, atividade_principal=AtividadePrincipal.MISTA,
    )
    return SolicitacaoCredito(**(base | kw))


def test_narrativa_contem_dados_essenciais():
    n = gerar_narrativa(_solicitacao())
    assert "45 anos" in n
    assert "R$" in n
    assert "80" in n  # área
    assert "mista" in n


def test_narrativa_destaca_queda_significativa():
    n = gerar_narrativa(_solicitacao(var_produtividade_pct=-20.0))
    assert "queda significativa" in n.lower()


def test_narrativa_nao_destaca_queda_pequena():
    n = gerar_narrativa(_solicitacao(var_produtividade_pct=-3.0))
    assert "queda significativa" not in n.lower()


def test_narrativa_eh_deterministica():
    s = _solicitacao()
    n1 = gerar_narrativa(s)
    n2 = gerar_narrativa(s)
    assert n1 == n2


def test_narrativa_aborda_renegociacoes():
    n = gerar_narrativa(_solicitacao(renegociacoes_recentes=3))
    assert "renegoci" in n.lower()


def test_narrativa_sem_renegociacoes_nao_menciona():
    n = gerar_narrativa(_solicitacao(renegociacoes_recentes=0))
    assert "renegociações" not in n.lower()


def test_narrativa_inclui_uf_e_ocupacao():
    n = gerar_narrativa(_solicitacao(uf="MT", cnae_ocupacao="Agricultura, pecuária"))
    assert "MT" in n
    assert "Agricultura" in n


def test_narrativa_diferencia_pf_pj():
    pf = gerar_narrativa(_solicitacao(tipo_cliente="PF"))
    pj = gerar_narrativa(_solicitacao(tipo_cliente="PJ"))
    assert pf != pj  # devem ter linguagens distintas
