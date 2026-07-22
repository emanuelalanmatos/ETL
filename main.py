"""Ponto de entrada do pipeline ETL de vendas.

Executa as três etapas em sequência:  Extract -> Transform -> Load
e exibe um resumo com os principais indicadores ao final.

Como executar (Windows):
    py main.py

Como executar (Linux/Mac):
    python3 main.py
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime

from etl import config, extract, load, transform


def setup_logging() -> None:
    """Configura o log para aparecer no terminal e em um arquivo (logs/etl.log)."""
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = config.LOGS_DIR / "etl.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),          # terminal
            logging.FileHandler(log_file, encoding="utf-8"),  # arquivo
        ],
    )


def imprimir_resumo(kpis: dict[str, float]) -> None:
    """Mostra um painel simples com os indicadores de negócio."""
    print("\n" + "=" * 48)
    print("        RESUMO DO PIPELINE DE VENDAS")
    print("=" * 48)
    print(f"  Pedidos processados .... {kpis['pedidos']:>12,}")
    print(f"  Itens vendidos ......... {kpis['itens_vendidos']:>12,}")
    print(f"  Receita bruta .......... R$ {kpis['receita_bruta']:>13,.2f}")
    print(f"  Desconto concedido ..... R$ {kpis['desconto_total']:>13,.2f}")
    print(f"  Receita líquida ........ R$ {kpis['receita_liquida']:>13,.2f}")
    print(f"  Ticket médio/pedido .... R$ {kpis['ticket_medio']:>13,.2f}")
    print("=" * 48 + "\n")


def main() -> int:
    """Orquestra o pipeline completo. Retorna 0 em sucesso, 1 em falha."""
    setup_logging()
    logger = logging.getLogger("main")

    inicio = datetime.now()
    logger.info("======== INÍCIO DO PIPELINE ETL ========")

    try:
        # 1. EXTRACT
        carts, users = extract.extract()

        # 2. TRANSFORM
        tabelas = transform.transform(carts, users)

        # 3. LOAD
        kpis = load.load(tabelas)

    except Exception:  # noqa: BLE001 — no topo do pipeline, queremos logar tudo
        logger.exception("Pipeline falhou. Veja o erro acima.")
        return 1

    duracao = (datetime.now() - inicio).total_seconds()
    logger.info("======== PIPELINE CONCLUÍDO em %.1fs ========", duracao)
    imprimir_resumo(kpis)
    return 0


if __name__ == "__main__":
    sys.exit(main())
