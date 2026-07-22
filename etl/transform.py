"""Etapa TRANSFORM — limpa, junta e enriquece os dados brutos.

O que acontece aqui:
  1. "Explode" cada pedido em uma linha por item vendido (tabela fato);
  2. Junta (JOIN) os itens com os dados de clientes;
  3. Calcula métricas de negócio (receita, desconto);
  4. Gera tabelas de resumo (por cidade e top produtos).

O resultado é um dicionário de DataFrames pronto para ser carregado.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd

logger = logging.getLogger(__name__)


def _build_customers_df(users: list[dict]) -> pd.DataFrame:
    """Cria a dimensão de clientes a partir dos dados brutos de usuários."""
    # json_normalize achata campos aninhados como 'address.city'
    df = pd.json_normalize(users)

    df = df[["id", "firstName", "lastName", "age", "gender", "address.city"]].copy()
    df = df.rename(
        columns={
            "id": "cliente_id",
            "firstName": "primeiro_nome",
            "lastName": "sobrenome",
            "age": "idade",
            "gender": "genero",
            "address.city": "cidade",
        }
    )
    df["cliente_nome"] = df["primeiro_nome"].str.strip() + " " + df["sobrenome"].str.strip()

    return df[["cliente_id", "cliente_nome", "cidade", "genero", "idade"]]


def _build_line_items_df(carts: list[dict]) -> pd.DataFrame:
    """Transforma pedidos aninhados em uma tabela fato (1 linha por item).

    Cada pedido ('cart') tem uma lista de produtos. Aqui achatamos essa
    estrutura para o formato tabular, que é o ideal para análise.
    """
    linhas: list[dict] = []

    for cart in carts:
        pedido_id = cart["id"]
        cliente_id = cart["userId"]

        for item in cart.get("products", []):
            receita_bruta = item["total"]  # price * quantity, já calculado pela API
            # Nome do campo de total com desconto mudou entre versões da API;
            # tratamos os dois casos e caímos no total bruto se ausente.
            receita_liquida = item.get(
                "discountedTotal", item.get("discountedPrice", receita_bruta)
            )

            linhas.append(
                {
                    "pedido_id": pedido_id,
                    "cliente_id": cliente_id,
                    "produto_id": item["id"],
                    "produto": item["title"],
                    "preco_unitario": item["price"],
                    "quantidade": item["quantity"],
                    "receita_bruta": receita_bruta,
                    "desconto_pct": item.get("discountPercentage", 0.0),
                    "receita_liquida": receita_liquida,
                }
            )

    df = pd.DataFrame(linhas)
    # Métrica derivada: quanto de desconto (em R$) foi concedido na linha
    df["valor_desconto"] = (df["receita_bruta"] - df["receita_liquida"]).round(2)
    return df


def _resumo_por_cidade(vendas: pd.DataFrame) -> pd.DataFrame:
    """Agrega a receita por cidade do cliente."""
    resumo = (
        vendas.groupby("cidade", as_index=False)
        .agg(
            pedidos=("pedido_id", "nunique"),
            itens_vendidos=("quantidade", "sum"),
            receita_liquida=("receita_liquida", "sum"),
        )
        .sort_values("receita_liquida", ascending=False)
        .reset_index(drop=True)
    )
    resumo["receita_liquida"] = resumo["receita_liquida"].round(2)
    return resumo


def _top_produtos(vendas: pd.DataFrame, limite: int = 10) -> pd.DataFrame:
    """Lista os produtos que mais geraram receita."""
    top = (
        vendas.groupby("produto", as_index=False)
        .agg(
            quantidade_vendida=("quantidade", "sum"),
            receita_liquida=("receita_liquida", "sum"),
        )
        .sort_values("receita_liquida", ascending=False)
        .head(limite)
        .reset_index(drop=True)
    )
    top["receita_liquida"] = top["receita_liquida"].round(2)
    return top


def transform(carts: list[dict], users: list[dict]) -> dict[str, pd.DataFrame]:
    """Executa a etapa completa de transformação.

    Returns:
        Dicionário {nome_da_tabela: DataFrame} pronto para a etapa de load.
    """
    logger.info("Transformando dados...")

    clientes = _build_customers_df(users)
    itens = _build_line_items_df(carts)

    # JOIN: enriquece cada item vendido com os dados do cliente (left join
    # para não perder vendas caso algum cliente não seja encontrado).
    vendas = itens.merge(clientes, on="cliente_id", how="left")

    # Marca temporal de quando o dado foi processado (rastreabilidade)
    vendas["extraido_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Ordena as colunas de forma lógica para leitura
    colunas = [
        "pedido_id", "cliente_id", "cliente_nome", "cidade", "genero", "idade",
        "produto_id", "produto", "preco_unitario", "quantidade",
        "receita_bruta", "desconto_pct", "valor_desconto", "receita_liquida",
        "extraido_em",
    ]
    vendas = vendas[colunas]

    # Verificação simples de qualidade: quantas cidades ficaram sem cliente?
    sem_cliente = int(vendas["cliente_nome"].isna().sum())
    if sem_cliente:
        logger.warning("%d itens sem cliente correspondente no JOIN.", sem_cliente)

    resultado = {
        "vendas": vendas,
        "resumo_por_cidade": _resumo_por_cidade(vendas),
        "top_produtos": _top_produtos(vendas),
    }

    logger.info(
        "  -> %d itens de venda em %d pedidos.",
        len(vendas), vendas["pedido_id"].nunique(),
    )
    return resultado
