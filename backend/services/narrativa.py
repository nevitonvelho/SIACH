from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.schemas import SolicitacaoCredito

_TEMPLATES_DIR = Path(__file__).parent.parent / "prompts"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(default=False),
    trim_blocks=True,
    lstrip_blocks=True,
)
_template = _env.get_template("narrativa.j2")


def gerar_narrativa(s: SolicitacaoCredito) -> str:
    """Converte um caso tabular em parágrafo descritivo determinístico."""
    return _template.render(
        uf=s.uf,
        tipo_cliente=s.tipo_cliente,
        cnae_ocupacao=s.cnae_ocupacao,
        submodalidade=s.submodalidade,
        idade=s.idade,
        renda_anual=s.renda_anual,
        estado_civil=s.estado_civil,
        dependentes=s.dependentes,
        tempo_emprego_meses=s.tempo_emprego_meses,
        valor_solicitado=s.valor_solicitado,
        prazo_meses=s.prazo_meses,
        finalidade=s.finalidade,
        score_interno=s.score_interno,
        divida_aberto=s.divida_aberto,
        tipo_garantia=s.tipo_garantia,
        area_propriedade_ha=s.area_propriedade_ha,
        var_produtividade_pct=s.var_produtividade_pct,
        renegociacoes_recentes=s.renegociacoes_recentes,
        atividade_principal=s.atividade_principal.value,
    ).strip()
