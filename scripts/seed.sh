#!/usr/bin/env bash
set -euo pipefail

# Gera casos sintéticos e popula SQLite
uv run python data/load_scrbcb.py

uv run python -c "
from backend.db import Base, get_engine
from backend.seed.load_data import carregar_csv_em_sqlite

engine = get_engine()
Base.metadata.create_all(engine)
n = carregar_csv_em_sqlite('data/casos_processados.csv', engine)
print(f'Carregados {n} casos.')
"
