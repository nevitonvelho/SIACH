#!/usr/bin/env bash
set -euo pipefail

# Gera casos sintéticos
uv run python data/load_scrbcb.py

# Carrega no SQLite e indexa no Chroma
uv run python -c "
from backend.db import Base, get_engine
from backend.seed.load_data import carregar_csv_em_sqlite, indexar_em_chroma

engine = get_engine()
Base.metadata.create_all(engine)
n = carregar_csv_em_sqlite('data/casos_processados.csv', engine)
print(f'Carregados {n} casos no SQLite.')
m = indexar_em_chroma(engine)
print(f'Indexados {m} casos no ChromaDB.')
"
