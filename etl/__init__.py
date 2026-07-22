"""Pacote ETL — pipeline de vendas (Extract, Transform, Load).

Fonte de dados: API pública DummyJSON (https://dummyjson.com).
Cada módulo cuida de uma etapa do pipeline:

    extract   -> coleta os dados brutos da API
    transform -> limpa, junta e calcula métricas de negócio
    load      -> grava o resultado em um banco SQLite e em CSV
"""

__version__ = "1.0.0"
