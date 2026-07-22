"""Configurações centrais do pipeline.

Manter tudo o que pode mudar (URLs, caminhos, parâmetros) em um único lugar
facilita a manutenção e evita "números mágicos" espalhados pelo código.
"""

from pathlib import Path

# Raiz do projeto = pasta que contém a pasta "etl"
BASE_DIR = Path(__file__).resolve().parent.parent

# Diretórios de saída
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# ---------------------------------------------------------------------------
# EXTRACT — fonte de dados (API pública DummyJSON)
# ---------------------------------------------------------------------------
API_BASE_URL = "https://dummyjson.com"
CARTS_ENDPOINT = f"{API_BASE_URL}/carts"   # "carrinhos" = pedidos de venda
USERS_ENDPOINT = f"{API_BASE_URL}/users"   # clientes

# A API responde 403 (Forbidden) sem um User-Agent de navegador.
# Este header é obrigatório para a extração funcionar.
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (ETL-Portfolio/1.0)",
}
REQUEST_TIMEOUT = 20   # segundos até desistir de uma requisição
MAX_RETRIES = 3        # tentativas em caso de falha de rede
PAGE_SIZE = 100        # itens por página na paginação da API

# ---------------------------------------------------------------------------
# LOAD — destino dos dados tratados
# ---------------------------------------------------------------------------
DATABASE_PATH = DATA_DIR / "vendas.db"      # banco SQLite de saída
SALES_CSV_PATH = DATA_DIR / "vendas.csv"    # cópia da tabela fato em CSV

# Nomes das tabelas geradas no banco
TABLE_SALES = "vendas"                 # tabela fato (1 linha por item vendido)
TABLE_CITY_SUMMARY = "resumo_por_cidade"
TABLE_TOP_PRODUCTS = "top_produtos"
