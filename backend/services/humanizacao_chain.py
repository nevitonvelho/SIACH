from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from backend.config import get_settings
from backend.schemas import AtividadePrincipal, ParecerTecnico

_TEMPLATES_DIR = Path(__file__).parent.parent / "prompts"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(default=False),
    trim_blocks=True,
    lstrip_blocks=True,
)
_template = _env.get_template("humanizacao_system.j2")


class HumanizacaoChain:
    def __init__(self, llm=None):
        if llm is None:
            s = get_settings()
            llm = ChatAnthropic(
                model=s.anthropic_model_humanizacao,
                api_key=s.anthropic_api_key,
                temperature=0.5,
                max_tokens=600,
            )
        self._llm = llm

    def run(
        self,
        parecer: ParecerTecnico,
        atividade_principal: AtividadePrincipal,
    ) -> str:
        prompt = _template.render(parecer=parecer, atividade_principal=atividade_principal)
        resp = self._llm.invoke([HumanMessage(content=prompt)])
        content = resp.content if isinstance(resp.content, str) else str(resp.content)
        return content.strip()
