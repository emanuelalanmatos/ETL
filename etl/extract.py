"""Etapa EXTRACT — coleta os dados brutos da API DummyJSON.

Responsabilidades desta etapa:
  * fazer as requisições HTTP com header, timeout e retentativas;
  * percorrer todas as páginas (paginação) da API;
  * devolver os dados brutos como listas de dicionários, sem tratamento.
"""

from __future__ import annotations

import logging
import time

import requests

from . import config

logger = logging.getLogger(__name__)


def _get(url: str, params: dict | None = None) -> dict:
    """Faz um GET com retentativas e backoff exponencial.

    Levanta RuntimeError se todas as tentativas falharem.
    """
    last_error: Exception | None = None

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            response = requests.get(
                url,
                params=params,
                headers=config.REQUEST_HEADERS,
                timeout=config.REQUEST_TIMEOUT,
            )
            response.raise_for_status()  # transforma 4xx/5xx em exceção
            return response.json()
        except requests.RequestException as error:
            last_error = error
            espera = 2 ** (attempt - 1)  # 1s, 2s, 4s...
            logger.warning(
                "Tentativa %d/%d falhou para %s (%s). Nova tentativa em %ds.",
                attempt, config.MAX_RETRIES, url, error, espera,
            )
            time.sleep(espera)

    raise RuntimeError(
        f"Não foi possível acessar {url} após {config.MAX_RETRIES} tentativas."
    ) from last_error


def _fetch_all(endpoint: str, data_key: str) -> list[dict]:
    """Coleta TODOS os registros de um endpoint paginado da DummyJSON.

    A API devolve um envelope com as chaves 'total', 'skip', 'limit' e a lista
    de dados (ex.: 'carts' ou 'users'). Aqui percorremos página a página até
    coletar tudo.
    """
    registros: list[dict] = []
    skip = 0

    while True:
        payload = _get(endpoint, params={"limit": config.PAGE_SIZE, "skip": skip})
        lote = payload.get(data_key, [])
        registros.extend(lote)

        total = payload.get("total", len(registros))
        skip += config.PAGE_SIZE

        logger.debug("%s: %d/%d coletados", data_key, len(registros), total)

        if not lote or skip >= total:
            break

    return registros


def extract_carts() -> list[dict]:
    """Extrai os pedidos (carrinhos) da API."""
    logger.info("Extraindo pedidos de %s ...", config.CARTS_ENDPOINT)
    carts = _fetch_all(config.CARTS_ENDPOINT, data_key="carts")
    logger.info("  -> %d pedidos extraídos.", len(carts))
    return carts


def extract_users() -> list[dict]:
    """Extrai os clientes da API (usados para enriquecer os pedidos)."""
    logger.info("Extraindo clientes de %s ...", config.USERS_ENDPOINT)
    users = _fetch_all(config.USERS_ENDPOINT, data_key="users")
    logger.info("  -> %d clientes extraídos.", len(users))
    return users


def extract() -> tuple[list[dict], list[dict]]:
    """Executa a etapa completa de extração.

    Returns:
        (carts, users): as duas fontes de dados brutas.
    """
    carts = extract_carts()
    users = extract_users()
    return carts, users
