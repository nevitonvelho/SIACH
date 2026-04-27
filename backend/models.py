from datetime import datetime
from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base


class Caso(Base):
    __tablename__ = "caso"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uf: Mapped[str] = mapped_column(String(2))
    tipo_cliente: Mapped[str] = mapped_column(String(2))
    cnae_ocupacao: Mapped[str] = mapped_column(String(128))
    submodalidade: Mapped[str] = mapped_column(String(32))
    idade: Mapped[int]
    renda_anual: Mapped[float] = mapped_column(Float)
    estado_civil: Mapped[str] = mapped_column(String(32))
    dependentes: Mapped[int]
    tempo_emprego_meses: Mapped[int]
    valor_solicitado: Mapped[float] = mapped_column(Float)
    prazo_meses: Mapped[int]
    finalidade: Mapped[str] = mapped_column(String(64))
    score_interno: Mapped[int]
    divida_aberto: Mapped[float] = mapped_column(Float)
    tipo_garantia: Mapped[str] = mapped_column(String(64))

    # Campos sintéticos rurais
    area_propriedade_ha: Mapped[float] = mapped_column(Float)
    var_produtividade_pct: Mapped[float] = mapped_column(Float)
    renegociacoes_recentes: Mapped[int]
    atividade_principal: Mapped[str] = mapped_column(String(32))

    decisao_final: Mapped[str] = mapped_column(String(32))
    inadimpliu: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class Decisao(Base):
    __tablename__ = "decisao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    solicitacao_id: Mapped[int]
    timestamp: Mapped[datetime] = mapped_column(DateTime)

    dados_solicitante: Mapped[dict] = mapped_column(JSON)
    casos_similares: Mapped[list] = mapped_column(JSON)

    parecer_tecnico: Mapped[str] = mapped_column(String)
    parecer_humanizado: Mapped[str] = mapped_column(String)
    recomendacao: Mapped[str] = mapped_column(String(32))
    confianca: Mapped[float] = mapped_column(Float)

    status_feedback: Mapped[str] = mapped_column(String(16), default="pendente")
    parecer_ajustado: Mapped[str | None] = mapped_column(String, nullable=True)
