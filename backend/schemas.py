from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Recomendacao(str, Enum):
    APROVADO = "aprovado"
    APROVADO_COM_RESSALVAS = "aprovado_com_ressalvas"
    RECUSADO = "recusado"


class AtividadePrincipal(str, Enum):
    AGRICULTURA = "agricultura"
    PECUARIA = "pecuaria"
    MISTA = "mista"


class SolicitacaoCredito(BaseModel):
    uf: str = Field(min_length=2, max_length=2)
    tipo_cliente: Literal["PF", "PJ"]
    cnae_ocupacao: str
    submodalidade: Literal["Custeio", "Investimento", "Comercializacao", "Industrializacao"]
    idade: int = Field(ge=18, le=100)
    renda_anual: float = Field(gt=0)
    estado_civil: str
    dependentes: int = Field(ge=0)
    tempo_emprego_meses: int = Field(ge=0)
    valor_solicitado: float = Field(gt=0)
    prazo_meses: int = Field(ge=6, le=60)
    finalidade: str
    score_interno: int = Field(ge=0, le=1000)
    divida_aberto: float = Field(ge=0)
    tipo_garantia: str

    area_propriedade_ha: float = Field(gt=0)
    var_produtividade_pct: float
    renegociacoes_recentes: int = Field(ge=0)
    atividade_principal: AtividadePrincipal


class CasoSimilar(BaseModel):
    caso_id: int
    score: float
    narrativa: str
    decisao_final: Recomendacao
    inadimpliu: bool | None = None


class ParecerTecnico(BaseModel):
    recomendacao: Recomendacao
    confianca: float = Field(ge=0.0, le=1.0)
    fatores_favoraveis: list[str]
    fatores_de_risco: list[str]
    comparacao_historica: str
    recomendacoes_acao: list[str]


class RespostaAnalise(BaseModel):
    decisao_id: int
    parecer_tecnico: ParecerTecnico
    parecer_humanizado: str
    casos_similares: list[CasoSimilar]


class FeedbackPayload(BaseModel):
    status: Literal["aprovado", "ajustado", "rejeitado"]
    parecer_ajustado: str | None = None

    @model_validator(mode="after")
    def _exige_texto_quando_ajustado(self):
        if self.status == "ajustado" and not self.parecer_ajustado:
            raise ValueError("parecer_ajustado é obrigatório quando status=ajustado")
        return self


class AvaliacaoPayload(BaseModel):
    analista: str = Field(min_length=1, max_length=64)
    decisao_id: int
    nota: int = Field(ge=0, le=10)
