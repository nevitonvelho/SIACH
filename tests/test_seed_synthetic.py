import pandas as pd
from data.load_scrbcb import mapear_decisao_final


def test_decisao_final_segue_score_e_inadimpliu():
    df = pd.DataFrame({
        "score_interno": [800, 500, 650, 650],
        "divida_aberto": [1_000, 50_000, 30_000, 30_000],
        "renda_anual": [100_000, 50_000, 100_000, 100_000],
        "inadimpliu":    [False,  True,    False,    True],
    })
    out = mapear_decisao_final(df)
    # score alto e dívida baixa → aprovado
    assert out.iloc[0] == "aprovado"
    # score baixo + dívida alta → recusado
    assert out.iloc[1] == "recusado"
    # caso intermediário sem inadimplência → com_ressalvas
    assert out.iloc[2] == "aprovado_com_ressalvas"
    # caso intermediário que inadimpliu → recusado
    assert out.iloc[3] == "recusado"
