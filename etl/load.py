"""Etapa LOAD — grava os dados tratados no destino final.

Destinos:
  * banco de dados SQLite (arquivo .db) com as três tabelas;
  * arquivo CSV com a tabela fato (fácil de abrir no Excel / visualizar).

A carga é idempotente: rodar o pipeline de novo substitui as tabelas
(if_exists="replace"), então não há duplicação de dados.
"""

from __future__ import annotations

import logging
import sqlite3

import pandas as pd

from . import config

logger = logging.getLogger(__name__)


def _calcular_kpis(vendas: pd.DataFrame) -> dict[str, float]:
    """Calcula indicadores-chave para exibir no resumo final."""
    num_pedidos = int(vendas["pedido_id"].nunique())
    receita_liquida = float(vendas["receita_liquida"].sum())

    return {
        "pedidos": num_pedidos,
        "itens_vendidos": int(vendas["quantidade"].sum()),
        "receita_bruta": round(float(vendas["receita_bruta"].sum()), 2),
        "desconto_total": round(float(vendas["valor_desconto"].sum()), 2),
        "receita_liquida": round(receita_liquida, 2),
        "ticket_medio": round(receita_liquida / num_pedidos, 2) if num_pedidos else 0.0,
    }


def load(tabelas: dict[str, pd.DataFrame]) -> dict[str, float]:
    """Executa a etapa completa de carga.

    Args:
        tabelas: dicionário {nome: DataFrame} vindo da transformação.

    Returns:
        Dicionário de KPIs calculados sobre a tabela de vendas.
    """
    logger.info("Carregando dados...")

    # Garante que a pasta de saída existe
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    vendas = tabelas["vendas"]

    # 1) CSV da tabela fato (encoding utf-8-sig abre acentos corretamente no Excel)
    vendas.to_csv(config.SALES_CSV_PATH, index=False, encoding="utf-8-sig")
    logger.info("  -> CSV salvo em %s", config.SALES_CSV_PATH)

    # 2) Banco SQLite com as três tabelas
    nomes = {
        "vendas": config.TABLE_SALES,
        "resumo_por_cidade": config.TABLE_CITY_SUMMARY,
        "top_produtos": config.TABLE_TOP_PRODUCTS,
    }
    with sqlite3.connect(config.DATABASE_PATH) as conn:
        for chave, df in tabelas.items():
            nome_tabela = nomes[chave]
            df.to_sql(nome_tabela, conn, if_exists="replace", index=False)
            logger.info("  -> Tabela '%s' (%d linhas) gravada no banco.", nome_tabela, len(df))

    logger.info("  -> Banco SQLite salvo em %s", config.DATABASE_PATH)

    return _calcular_kpis(vendas)
