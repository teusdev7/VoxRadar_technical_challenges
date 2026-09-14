import logging
import time
from typing import Any

import httpx

from kwai_collector.config import settings

logger = logging.getLogger(__name__)


def get_profile_page(
    user_id: str,
    pcursor: str = "",
    max_tentativas: int = settings.max_tentativas,
    backoff_base: float = settings.backoff_base,
) -> tuple[list[dict[str, Any]], str | None]:
    url = "https://www.kwai.com/rest/o/w/pc/feed/profile"

    payload = {
        "beforePage": "",
        "count": 20,
        "fromPage": "PC_PROFILE",
        "pcursor": pcursor,
        "userId": user_id,
    }

    headers = {
        "Content-Type": "application/json",
        "accept": "application/json, text/plain, */*",
    }

    for tentativa in range(1, max_tentativas + 1):
        try:
            response = httpx.post(
                url,
                json=payload,
                headers=headers,
            )
        except httpx.RequestError:
            if tentativa == max_tentativas:
                raise

            espera = backoff_base * (2 ** (tentativa - 1))

            logger.warning(
                "Erro de conexão. Nova tentativa em %.1fs.",
                espera,
            )

            time.sleep(espera)
            continue

        if response.status_code == 429 or response.status_code >= 500:
            if tentativa == max_tentativas:
                response.raise_for_status()

            espera = backoff_base * (2 ** (tentativa - 1))

            logger.warning(
                "Kwai respondeu HTTP %d. Nova tentativa em %.1fs.",
                response.status_code,
                espera,
            )

            time.sleep(espera)
            continue

        response.raise_for_status()

        dados = response.json()

        feeds = dados.get("feeds", [])
        cursor = dados.get("cursor")

        return feeds, cursor

    raise RuntimeError("Não foi possível obter a página do perfil.")

def get_all_profile_posts(
    user_id: str,
    max_paginas: int = 5,
    delay: float = settings.delay,
) -> list[dict[str, Any]]:
    resultados: list[dict[str, Any]] = []
    ids_vistos: set[str] = set()

    pcursor = ""

    for pagina in range(max_paginas):
        if pagina > 0 and delay > 0:
            time.sleep(delay)

        feeds, novo_cursor = get_profile_page(
            user_id=user_id,
            pcursor=pcursor,
        )

        if not feeds:
            break

        for post in feeds:
            post_id = post.get("photo_id_str")

            if post_id is not None and post_id in ids_vistos:
                continue

            if post_id is not None:
                ids_vistos.add(post_id)

            resultados.append(post)

        if not novo_cursor:
            break

        if novo_cursor == pcursor:
            break

        pcursor = novo_cursor

    return resultados
