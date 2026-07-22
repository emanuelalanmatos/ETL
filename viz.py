"""Camada de visualização — acesso ao banco e construção dos gráficos.

Este módulo NÃO importa o Streamlit de propósito: assim as funções podem ser
testadas isoladamente (só pandas + matplotlib). O dashboard (dashboard.py) é
que junta tudo na interface web.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from etl import config

# --- Paleta e cores (paleta validada para daltonismo/contraste) -------------
AZUL = "#2a78d6"          # cor primária das barras (magnitude)
TINTA_PRIMARIA = "#0b0b0b"   # texto principal (rótulos de categoria)
TINTA_SECUNDARIA = "#52514e"  # texto de apoio (valores)


def aplicar_estilo() -> None:
    """Define um estilo global limpo para todos os gráficos matplotlib."""
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans"],
            "figure.autolayout": True,
            "axes.edgecolor": TINTA_SECUNDARIA,
            "text.color": TINTA_PRIMARIA,
        }
    )


# --- Formatação de valores em Real (R$) -------------------------------------
def fmt_brl(valor: float) -> str:
    """Formata no padrão brasileiro: R$ 3.456.709,58."""
    s = f"{valor:,.2f}"                       # 3,456,709.58 (padrão EUA)
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def fmt_brl_compacto(valor: float) -> str:
    """Formato curto para caber nos gráficos: R$ 3,5M / R$ 587k."""
    if valor >= 1_000_000:
        return f"R$ {valor / 1_000_000:.1f}M".replace(".", ",")
    if valor >= 1_000:
        return f"R$ {valor / 1_000:.0f}k"
    return f"R$ {valor:.0f}"


# --- Acesso a dados ----------------------------------------------------------
def load_vendas(db_path: Path | str = config.DATABASE_PATH) -> pd.DataFrame:
    """Lê a tabela fato 'vendas' do banco SQLite gerado pelo ETL."""
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql(f"SELECT * FROM {config.TABLE_SALES}", conn)


def aplicar_filtros(
    df: pd.DataFrame,
    cidades: list[str] | None = None,
    generos: list[str] | None = None,
) -> pd.DataFrame:
    """Filtra as vendas por cidade e/ou gênero (lista vazia = sem filtro)."""
    filtrado = df
    if cidades:
        filtrado = filtrado[filtrado["cidade"].isin(cidades)]
    if generos:
        filtrado = filtrado[filtrado["genero"].isin(generos)]
    return filtrado


def compute_kpis(df: pd.DataFrame) -> dict[str, float]:
    """Calcula os indicadores principais sobre um recorte das vendas."""
    num_pedidos = int(df["pedido_id"].nunique())
    receita_liquida = float(df["receita_liquida"].sum())
    return {
        "pedidos": num_pedidos,
        "itens_vendidos": int(df["quantidade"].sum()),
        "receita_bruta": float(df["receita_bruta"].sum()),
        "desconto_total": float(df["valor_desconto"].sum()),
        "receita_liquida": receita_liquida,
        "ticket_medio": receita_liquida / num_pedidos if num_pedidos else 0.0,
    }


def top_produtos(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Ranking dos produtos por receita líquida (ordenado do maior p/ o menor)."""
    return (
        df.groupby("produto", as_index=False)["receita_liquida"]
        .sum()
        .sort_values("receita_liquida", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


def receita_por_cidade(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Receita líquida agregada por cidade (top n)."""
    return (
        df.groupby("cidade", as_index=False)["receita_liquida"]
        .sum()
        .sort_values("receita_liquida", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


# --- Gráficos ----------------------------------------------------------------
def grafico_barras(
    df: pd.DataFrame,
    coluna_categoria: str,
    coluna_valor: str,
    *,
    cor: str = AZUL,
    altura: float = 4.2,
) -> plt.Figure:
    """Barra horizontal de magnitude, uma cor só, com rótulos diretos.

    Segue boas práticas de dataviz: eixo único, sem excesso de cromo
    (linhas de grade/eixos), maior valor no topo e o número escrito na
    ponta de cada barra (dispensando eixo X).
    """
    aplicar_estilo()

    categorias = df[coluna_categoria].tolist()
    valores = df[coluna_valor].tolist()

    fig, ax = plt.subplots(figsize=(6.4, altura))
    fig.patch.set_alpha(0.0)   # fundo transparente (integra ao tema do app)
    ax.patch.set_alpha(0.0)

    posicoes = range(len(categorias))
    barras = ax.barh(list(posicoes), valores, color=cor, height=0.66, zorder=3)

    ax.set_yticks(list(posicoes), categorias)
    ax.invert_yaxis()  # maior no topo (df já vem ordenado desc)

    # Remove todo o cromo desnecessário
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([])
    ax.tick_params(length=0, labelcolor=TINTA_PRIMARIA)

    # Espaço à direita para o rótulo do valor não cortar
    maximo = max(valores) if valores else 0
    ax.set_xlim(0, maximo * 1.20 if maximo else 1)

    # Rótulo do valor na ponta de cada barra
    for barra, valor in zip(barras, valores):
        ax.text(
            barra.get_width() + maximo * 0.015,
            barra.get_y() + barra.get_height() / 2,
            fmt_brl_compacto(valor),
            va="center", ha="left", fontsize=9, color=TINTA_SECUNDARIA,
        )

    return fig
