"""Fixtures compartilhadas pelos testes.

O pytest carrega este arquivo sozinho — nenhum teste precisa importá-lo. Basta
declarar o nome da fixture como argumento da função de teste.
"""
import os

import pandas as pd
import pytest
from sqlalchemy import text

TABELA_DE_TESTE = "cotacoes_teste"


@pytest.fixture(scope="session")
def engine():
    """Conexão com o Postgres de teste — ou pula os testes que dependem dele.

    NA MÁQUINA DE ALGUÉM: pular, nunca falhar. Quem clonou o repositório e ainda
    não subiu o Docker não deve ver a suíte vermelha por isso — mas o motivo
    aparece no relatório, então também não vira silêncio.

    NO CI: `EXIGE_POSTGRES=1` transforma o pulo em falha. Lá, pular é o mesmo
    que não testar: o build ficaria verde sem ter exercitado a idempotência,
    que é justamente o que o CI existe para proteger.
    """
    from etl.load import get_engine

    try:
        eng = get_engine()
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        motivo = (
            f"Postgres indisponível ({type(exc).__name__}). Suba com: "
            "docker compose -f docker-compose.data.yml up -d postgres"
        )
        if os.getenv("EXIGE_POSTGRES") == "1":
            pytest.fail(motivo, pytrace=False)
        pytest.skip(motivo)
    return eng


@pytest.fixture
def tabela(engine):
    """Tabela descartável, limpa antes e depois de cada teste.

    Nunca usar a `cotacoes` real: teste que suja dado de produção é teste que
    ninguém roda. A tabela nasce da própria DDL do load.py — é ela que está
    sob teste, não uma cópia escrita à mão aqui.
    """
    def _dropa():
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {TABELA_DE_TESTE}"))

    _dropa()
    yield TABELA_DE_TESTE
    _dropa()


@pytest.fixture
def conta(engine):
    """Quantas linhas há na tabela agora."""
    def _conta(tabela: str) -> int:
        with engine.connect() as conn:
            return conn.execute(text(f"SELECT count(*) FROM {tabela}")).scalar()

    return _conta


@pytest.fixture
def lote():
    """Lote no formato que o transform entrega — não um DataFrame inventado.

    Passa pelo `transformar_cotacoes` de verdade, então o teste também cobre a
    costura entre as etapas 4 e 5: se o transform mudar o tipo de uma coluna, é
    aqui que aparece.
    """
    from etl.transform import transformar_cotacoes

    def _lote(pares=(("USD-BRL", "5.12"), ("EUR-BRL", "6.03")), ts="2026-09-28 10:00:00"):
        cru = pd.DataFrame(
            [{"par": p, "valor": v, "ts": ts} for p, v in pares]
        )
        return transformar_cotacoes(cru)

    return _lote
