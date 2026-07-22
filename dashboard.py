"""Dashboard de Vendas — interface web interativa (Streamlit).

Lê o banco 'data/vendas.db' gerado pelo pipeline ETL e mostra KPIs,
gráficos e uma tabela, com filtros por cidade e gênero.

Como executar:
    streamlit run dashboard.py
"""

from __future__ import annotations

import streamlit as st

import viz
from etl import config

# --- Configuração da página --------------------------------------------------
st.set_page_config(page_title="Dashboard de Vendas", page_icon="🛒", layout="wide")


@st.cache_data
def carregar_dados():
    """Carrega a tabela de vendas (em cache para não reler o banco a cada clique)."""
    return viz.load_vendas()


# --- Verifica se o ETL já foi executado -------------------------------------
if not config.DATABASE_PATH.exists():
    st.error(
        "Banco de dados não encontrado. Rode o pipeline ETL primeiro:\n\n"
        "```\npython main.py\n```"
    )
    st.stop()

vendas = carregar_dados()

# --- Cabeçalho ---------------------------------------------------------------
st.title("🛒 Dashboard de Vendas")
st.caption(
    "Dados extraídos da API DummyJSON e processados pelo pipeline ETL. "
    "Use os filtros na barra lateral para explorar."
)

# --- Filtros (barra lateral) -------------------------------------------------
st.sidebar.header("Filtros")
cidades = st.sidebar.multiselect(
    "Cidade", options=sorted(vendas["cidade"].dropna().unique())
)
generos = st.sidebar.multiselect(
    "Gênero", options=sorted(vendas["genero"].dropna().unique())
)

df = viz.aplicar_filtros(vendas, cidades, generos)

if df.empty:
    st.warning("Nenhuma venda encontrada para os filtros selecionados.")
    st.stop()

# --- KPIs (cartões de destaque) ---------------------------------------------
kpis = viz.compute_kpis(df)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Pedidos", f"{kpis['pedidos']:,}".replace(",", "."))
c2.metric("Itens vendidos", f"{kpis['itens_vendidos']:,}".replace(",", "."))
c3.metric("Receita líquida", viz.fmt_brl(kpis["receita_liquida"]))
c4.metric("Ticket médio", viz.fmt_brl(kpis["ticket_medio"]))

st.divider()

# --- Gráficos (lado a lado) --------------------------------------------------
col_esq, col_dir = st.columns(2)

with col_esq:
    st.subheader("Top 10 produtos por receita")
    fig_prod = viz.grafico_barras(viz.top_produtos(df), "produto", "receita_liquida")
    st.pyplot(fig_prod, width="stretch")

with col_dir:
    st.subheader("Receita por cidade (top 10)")
    fig_cidade = viz.grafico_barras(viz.receita_por_cidade(df), "cidade", "receita_liquida")
    st.pyplot(fig_cidade, width="stretch")

st.divider()

# --- Tabela detalhada --------------------------------------------------------
st.subheader("Vendas detalhadas")
st.caption(f"{len(df):,} itens de venda no recorte atual.".replace(",", "."))
st.dataframe(df, width="stretch", hide_index=True)
