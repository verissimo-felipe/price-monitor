"""Etapa 5 — Carga no PostgreSQL: configurada por ambiente e IDEMPOTENTE."""
from __future__ import annotations

import os
import re

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()


# Nome de tabela NÃO pode ser parâmetro ligado (:x) em SQL — só valores podem.
# Como ele entra por interpolação de string, validar é a única defesa contra
# injeção. Aceita apenas identificador simples: letras, dígitos e underscore.
_NOME_DE_TABELA = re.compile(r"[a-z_][a-z0-9_]{0,62}", re.IGNORECASE)


def _valida_tabela(tabela: str) -> str:
    if not _NOME_DE_TABELA.fullmatch(tabela):
        raise ValueError(f"nome de tabela inválido: {tabela!r}")
    return tabela


def _ddl(tabela: str) -> str:
    return f"""
CREATE TABLE IF NOT EXISTS {tabela} (
    id     BIGSERIAL PRIMARY KEY,
    par    TEXT          NOT NULL,
    valor  NUMERIC(18,6) NOT NULL,
    ts     TIMESTAMP     NOT NULL,
    -- A chave natural do dado. É ela que torna a carga idempotente.
    CONSTRAINT uq_{tabela}_par_ts UNIQUE (par, ts)
);
"""


def _upsert(tabela: str) -> str:
    return f"""
INSERT INTO {tabela} (par, valor, ts)
VALUES (:par, :valor, :ts)
ON CONFLICT (par, ts) DO NOTHING;
"""



def get_engine() -> Engine:
    """Monta a conexão a partir do ambiente — nunca de credencial no código."""
    faltando = [v for v in ("DB_USER", "DB_PASSWORD", "DB_NAME") if not os.getenv(v)]
    if faltando:
        raise RuntimeError(
            f"variáveis de ambiente ausentes: {faltando} (veja .env.example)"
        )

    url = (
        f"postgresql+psycopg2://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
        f"/{os.environ['DB_NAME']}"
    )
    # pool_pre_ping evita erro de conexão morta em pipeline que roda de hora em hora
    return create_engine(url, pool_pre_ping=True)


def carregar(df: pd.DataFrame, tabela: str = "cotacoes") -> int:
    """Insere as cotações ignorando o que já existe. Retorna as linhas enviadas.

    IDEMPOTENTE: rodar duas vezes com o mesmo lote não duplica nada, porque a
    constraint UNIQUE(par, ts) + ON CONFLICT DO NOTHING descartam a repetição.
    Sem isso, o `retries: 2` da DAG duplicaria dados a cada falha parcial.
    """
    _valida_tabela(tabela)

    if df.empty:
        return 0

    registros = df[["par", "valor", "ts"]].to_dict("records")
    engine = get_engine()
    with engine.begin() as conn:  # begin() = commit no fim, rollback no erro
        conn.execute(text(_ddl(tabela)))
        conn.execute(text(_upsert(tabela)), registros)
    return len(registros)
