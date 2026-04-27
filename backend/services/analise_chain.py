"""
Etapa 4 do pipeline: análise técnica via Claude Sonnet, com saída JSON
validada por Pydantic. Retry simples com prompt-de-correção em falha de parse.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from backend.config import get_settings
from backend.schemas import CasoSimilar, ParecerTecnico

_TEMPLATES_DIR = Path(__file__).parent.parent / "prompts"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(default=False),
    trim_blocks=True,
    lstrip_blocks=True,
)
_template = _env.get_template("analise_system.j2")

_BLOCO_JSON = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_PRIMEIRO_OBJETO = re.compile(r"(\{.*\})", re.DOTALL)


class JsonParseFailure(Exception):
    pass


class AnaliseChain:
    def __init__(self, llm=None, max_retries: int = 2):
        if llm is None:
            s = get_settings()
            llm = ChatAnthropic(
                model=s.anthropic_model_analise,
                api_key=s.anthropic_api_key,
                temperature=0.2,
                max_tokens=1500,
            )
        self._llm = llm
        self._max_retries = max_retries

    def run(self, narrativa: str, casos_similares: list[CasoSimilar]) -> ParecerTecnico:
        prompt = _template.render(narrativa_atual=narrativa, casos_similares=casos_similares)
        last_err: Exception | None = None

        for attempt in range(self._max_retries):
            resp = self._llm.invoke([HumanMessage(content=prompt)])
            content = resp.content if isinstance(resp.content, str) else str(resp.content)
            try:
                return self._parse(content)
            except Exception as e:
                last_err = e
                # Reforça instrução no retry
                prompt = (
                    prompt
                    + "\n\nATENÇÃO: sua resposta anterior não pôde ser interpretada como"
                    + " JSON válido. Responda agora com APENAS o objeto JSON, sem texto"
                    + " antes ou depois, sem blocos markdown."
                )

        raise JsonParseFailure(f"Falha após {self._max_retries} tentativas: {last_err}")

    @staticmethod
    def _parse(content: str) -> ParecerTecnico:
        # 1) tenta bloco markdown ```json ... ```
        if (m := _BLOCO_JSON.search(content)):
            return ParecerTecnico.model_validate_json(m.group(1))
        # 2) tenta primeiro objeto JSON encontrado
        if (m := _PRIMEIRO_OBJETO.search(content)):
            return ParecerTecnico.model_validate_json(m.group(1))
        # 3) tenta o conteúdo inteiro
        return ParecerTecnico.model_validate(json.loads(content))
