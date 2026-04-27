from pathlib import Path
import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.db import Base
from backend.models import Caso
from backend.seed.load_data import carregar_csv_em_sqlite


@pytest.fixture
def csv_minimo(tmp_path: Path) -> Path:
    df = pd.DataFrame([
        {
            "uf": "PR", "tipo_cliente": "PF", "cnae_ocupacao": "Empresário",
            "submodalidade": "Custeio",
            "idade": 35, "renda_anual": 80_000, "estado_civil": "casado",
            "dependentes": 1, "tempo_emprego_meses": 36,
            "valor_solicitado": 20_000, "prazo_meses": 24,
            "finalidade": "custeio_agricola", "score_interno": 700,
            "divida_aberto": 5_000, "tipo_garantia": "fiador",
            "area_propriedade_ha": 50.0, "var_produtividade_pct": -2.0,
            "renegociacoes_recentes": 0, "atividade_principal": "agricultura",
            "inadimpliu": False,
        },
        {
            "uf": "SP", "tipo_cliente": "PJ", "cnae_ocupacao": "Agricultura, pecuária",
            "submodalidade": "Investimento",
            "idade": 60, "renda_anual": 30_000, "estado_civil": "solteiro",
            "dependentes": 0, "tempo_emprego_meses": 12,
            "valor_solicitado": 15_000, "prazo_meses": 36,
            "finalidade": "custeio_agricola", "score_interno": 500,
            "divida_aberto": 12_000, "tipo_garantia": "sem_garantia",
            "area_propriedade_ha": 20.0, "var_produtividade_pct": -12.0,
            "renegociacoes_recentes": 2, "atividade_principal": "mista",
            "inadimpliu": True,
        },
    ])
    p = tmp_path / "in.csv"
    df.to_csv(p, index=False)
    return p


def test_carrega_csv_em_sqlite(csv_minimo, tmp_path):
    db_url = f"sqlite:///{tmp_path/'test.db'}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    n = carregar_csv_em_sqlite(str(csv_minimo), engine)
    assert n == 2

    with Session(engine) as s:
        casos = s.scalars(select(Caso)).all()
        assert len(casos) == 2
        # novos campos presentes
        assert casos[0].uf == "PR"
        assert casos[0].tipo_cliente == "PF"
        # campos rurais preservados
        assert all(c.area_propriedade_ha > 0 for c in casos)
        assert all(c.atividade_principal in {"agricultura", "pecuaria", "mista"} for c in casos)
        # decisao_final mapeada
        assert all(c.decisao_final in {"aprovado", "aprovado_com_ressalvas", "recusado"} for c in casos)
