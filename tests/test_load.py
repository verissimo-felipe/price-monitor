"""Testes da carga idempotente (etl/load.py).

POR QUE CONTRA O POSTGRES DE VERDADE:
a idempotência não está no código Python — está na constraint UNIQUE(par, ts) e
no ON CONFLICT DO NOTHING, que quem executa é o banco. Testar isso contra um
SQLite em memória provaria que o SQLite funciona, não que a NOSSA DDL está
certa. Sem banco de pé, estes testes são pulados (veja conftest.py).
"""
import pandas as pd
import pytest
from sqlalchemy import text

from etl.load import carregar


def test_carga_dupla_nao_duplica(tabela, lote, conta):
    """A garantia central do pipeline.

    Sem ela, o `retries: 2` da DAG duplica dados em silêncio: a task falha na
    metade, o retry regrava o lote inteiro, a execução fica verde e o relatório
    sai inflado. É o pior tipo de bug — o que não avisa.
    """
    carregar(lote(), tabela)
    carregar(lote(), tabela)          # exatamente o que o retry faz

    assert conta(tabela) == 2


def test_retorno_conta_linhas_enviadas_nao_inseridas(tabela, lote):
    """O retorno é quantas linhas foram MANDADAS, não quantas entraram.

    Fixa o contrato por escrito: na segunda chamada nada é inserido, e ainda
    assim o retorno é 2. Quem quiser saber o que entrou de fato tem que
    consultar a tabela.
    """
    assert carregar(lote(), tabela) == 2
    assert carregar(lote(), tabela) == 2


def test_linha_nova_entra_sem_afetar_as_existentes(tabela, lote, conta):
    """Idempotência não pode virar 'a carga parou de funcionar'."""
    carregar(lote(), tabela)
    carregar(lote(ts="2026-09-28 11:00:00"), tabela)

    assert conta(tabela) == 4


def test_valor_diferente_no_mesmo_par_e_ts_nao_sobrescreve(tabela, lote, engine):
    """DO NOTHING, não DO UPDATE: a primeira leitura vence.

    É uma decisão, não um acaso — cotação já gravada para um instante não muda
    retroativamente. Se um dia a regra passar a ser 'a última vence', é este
    teste que vai falhar e obrigar a decisão a ser explícita.
    """
    carregar(lote(pares=(("USD-BRL", "5.12"),)), tabela)
    carregar(lote(pares=(("USD-BRL", "9.99"),)), tabela)

    with engine.connect() as conn:
        valor = conn.execute(text(f"SELECT valor FROM {tabela}")).scalar()

    assert float(valor) == 5.12


def test_dataframe_vazio_nao_toca_no_banco(tabela):
    """Extração que veio vazia não é erro — é dia sem dado."""
    vazio = pd.DataFrame(columns=["par", "valor", "ts"])

    assert carregar(vazio, tabela) == 0


def test_nome_de_tabela_invalido_e_recusado():
    """O nome da tabela entra por interpolação, então tem que ser validado.

    Não precisa de banco: a recusa acontece antes de qualquer conexão.
    """
    with pytest.raises(ValueError, match="inválido"):
        carregar(pd.DataFrame({"par": ["x"], "valor": [1.0], "ts": [pd.Timestamp.now()]}),
                 "cotacoes; DROP TABLE cotacoes")
