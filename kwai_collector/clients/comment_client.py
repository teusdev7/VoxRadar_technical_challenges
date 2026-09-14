from collections.abc import Mapping
from time import sleep
from typing import Any

import httpx

from kwai_collector.config import settings

A1_Radar = "A1_Radar"


# ============================================================
# WEB / PC
# ============================================================

BASE_URL = "https://www.kwai.com"

ROOT_COMMENTS_ENDPOINT = "/rest/o/w/pc/getComments/list"
SUB_COMMENTS_ENDPOINT = "/rest/o/w/pc/getSubComments/list"


# ============================================================
# TINY / ANDROID
# ============================================================

# Hosts encontrados no res/raw/fp do APK do Kwai.
TINY_BASE_URLS = (
    "https://api.kwai-pro.com",
    "https://api.kwaipros.com",
)

# Host principal.
TINY_BASE_URL = TINY_BASE_URLS[0]

# Endpoint encontrado no APK.
TINY_COMMENTS_ENDPOINT = "/rest/o/lite/comment/list"


# ============================================================
# HTTP
# ============================================================

DEFAULT_TIMEOUT = 20.0


DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Content-Type": "application/json",
    "Origin": "https://www.kwai.com",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/152.0.0.0 Safari/537.36"
    ),
}


TINY_HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "pt-BR",
    "User-Agent": "kwai-android",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


# ============================================================
# EXCEPTIONS
# ============================================================


class KwaiCommentsError(RuntimeError):
    """Erro relacionado à coleta de comentários do Kwai."""


# ============================================================
# CLIENTE WEB / PC
# ============================================================


def create_client(
    cookies: dict[str, str] | None = None,
    cookie_header: str | None = None,
) -> httpx.Client:
    headers = dict(DEFAULT_HEADERS)

    effective_cookie = (
        cookie_header
        if cookie_header is not None
        else settings.cookie
    )

    if cookies is None and effective_cookie:
        headers["Cookie"] = effective_cookie

    return httpx.Client(
        base_url=BASE_URL,
        headers=headers,
        cookies=cookies,
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
    )


# ============================================================
# CLIENTE TINY / ANDROID
# ============================================================


def create_tiny_client(
    base_url: str = TINY_BASE_URL,
    *,
    headers: Mapping[str, str] | None = None,
    cookies: dict[str, str] | None = None,
) -> httpx.Client:
    """
    Cria um cliente para o fluxo Tiny/Android encontrado no APK.

    Host principal:
        https://api.kwai-pro.com

    Fallback:
        https://api.kwaipros.com

    Não definimos Content-Type manualmente.

    O endpoint Tiny usa FormBody e, portanto, quando usamos:

        data={...}

    o httpx gera application/x-www-form-urlencoded.
    """

    final_headers = dict(TINY_HEADERS)

    if headers:
        final_headers.update(headers)

    return httpx.Client(
        base_url=base_url.rstrip("/"),
        headers=final_headers,
        cookies=cookies,
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
    )


# ============================================================
# POST WEB / PC
# ============================================================


def _post(
    endpoint: str,
    payload: dict[str, Any],
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    owns_client = client is None

    if client is None:
        client = create_client()

    try:
        response = client.post(
            endpoint,
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            raise KwaiCommentsError(
                "A resposta do Kwai não é um objeto JSON."
            )

        return data

    except httpx.HTTPStatusError as exc:
        raise KwaiCommentsError(
            f"Erro HTTP {exc.response.status_code} "
            f"ao acessar {endpoint}"
        ) from exc

    except httpx.RequestError as exc:
        raise KwaiCommentsError(
            f"Erro de conexão com o Kwai: {exc}"
        ) from exc

    except ValueError as exc:
        raise KwaiCommentsError(
            "O Kwai retornou uma resposta que não é JSON."
        ) from exc

    finally:
        if owns_client:
            client.close()


# ============================================================
# COMENTÁRIOS WEB / PC
# ============================================================


def get_comments(
    photo_id: str,
    cursor: str = "",
    root_comment_count: int = 10,
    sub_comment_count: int = 2,
    *,
    client: httpx.Client | None = None,
) -> tuple[list[dict[str, Any]], str]:
    payload = {
        "photo_id": str(photo_id),
        "cursor": cursor,
        "rootCommentCount": root_comment_count,
        "subCommentCount": sub_comment_count,
    }

    data = _post(
        ROOT_COMMENTS_ENDPOINT,
        payload,
        client=client,
    )

    result = data.get("result")

    if result != 1:
        raise KwaiCommentsError(
            "A API de comentários retornou erro. "
            f"result={result!r} "
            f"error_msg={data.get('error_msg')!r}"
        )

    if (
        "host-name" in data
        and "rootComments" not in data
    ):
        raise KwaiCommentsError(
            "O Kwai respondeu com result=1, mas não enviou "
            "'rootComments'. A sessão atual pode não ter permissão "
            "para acessar a lista completa de comentários."
        )

    comments_raw = data.get("rootComments")

    if not isinstance(comments_raw, list):
        comments: list[dict[str, Any]] = []
    else:
        comments = [
            item
            for item in comments_raw
            if isinstance(item, dict)
        ]

    next_cursor = data.get("cursor")

    if next_cursor in (None, ""):
        next_cursor = "no_more"

    return comments, str(next_cursor)


def get_subcomments(
    photo_id: str,
    root_comment_id: str,
    cursor: str = "",
    sub_comment_count: int | None = None,
    *,
    client: httpx.Client | None = None,
) -> tuple[list[dict[str, Any]], str]:
    if sub_comment_count is None:
        sub_comment_count = 3 if cursor else 5

    payload = {
        "photo_id": str(photo_id),
        "cursor": cursor,
        "rootCommentId": str(root_comment_id),
        "subCommentCount": sub_comment_count,
    }

    data = _post(
        SUB_COMMENTS_ENDPOINT,
        payload,
        client=client,
    )

    result = data.get("result")

    if result != 1:
        raise KwaiCommentsError(
            "A API de respostas retornou erro. "
            f"result={result!r} "
            f"error_msg={data.get('error_msg')!r}"
        )

    subcomments_raw = data.get("subComments")

    if not isinstance(subcomments_raw, list):
        subcomments: list[dict[str, Any]] = []
    else:
        subcomments = [
            item
            for item in subcomments_raw
            if isinstance(item, dict)
        ]

    next_cursor = data.get("cursor")

    if next_cursor in (None, ""):
        next_cursor = "no_more"

    return subcomments, str(next_cursor)


# ============================================================
# TINY / ANDROID
# ============================================================


def get_tiny_comments(
    photo_id: str,
    *,
    base_url: str = TINY_BASE_URL,
    query_params: Mapping[str, str] | None = None,
    form_params: Mapping[str, str] | None = None,
    headers: Mapping[str, str] | None = None,
    client: httpx.Client | None = None,
    debug: bool = False,
) -> list[dict[str, Any]]:
    """
    Busca comentários pelo endpoint Tiny/Android.

    Endpoint:
        POST /rest/o/lite/comment/list

    Host padrão:
        https://api.kwai-pro.com

    Estrutura encontrada no APK:

    QUERY:
        parâmetros comuns do aplicativo

    BODY:
        photo_id
        + parâmetros comuns
        + parâmetros adicionais do body
    """

    owns_client = client is None

    if client is None:
        client = create_tiny_client(
            base_url=base_url,
            headers=headers,
        )

    # --------------------------------------------------------
    # QUERY STRING
    # --------------------------------------------------------

    params: dict[str, str] = {
        str(key): str(value)
        for key, value in (query_params or {}).items()
    }

    # --------------------------------------------------------
    # BODY / FORM
    # --------------------------------------------------------

    body: dict[str, str] = {
        "photo_id": str(photo_id),
    }

    # O APK copia os parâmetros comuns da query
    # também para o FormBody.
    body.update(params)

    # Parâmetros adicionais exclusivos do body.
    if form_params:
        body.update(
            {
                str(key): str(value)
                for key, value in form_params.items()
            }
        )

    try:
        response = client.post(
            TINY_COMMENTS_ENDPOINT,
            params=params,
            data=body,
        )

        # ----------------------------------------------------
        # DEBUG
        # ----------------------------------------------------

        if debug:
            print()
            print("=" * 60)
            print("TINY REQUEST")
            print("=" * 60)

            print(
                "METHOD:",
                response.request.method,
            )

            print(
                "URL:",
                response.request.url,
            )

            print(
                "BODY KEYS:",
                sorted(body.keys()),
            )

            print(
                "QUERY KEYS:",
                sorted(params.keys()),
            )

            print()

            print("=" * 60)
            print("TINY RESPONSE")
            print("=" * 60)

            print(
                "STATUS:",
                response.status_code,
            )

            print(
                "CONTENT-TYPE:",
                response.headers.get(
                    "content-type"
                ),
            )

            print(
                "BODY COMPLETO:",
                response.text,
            )

            print("=" * 60)
            print()

        # ----------------------------------------------------
        # HTTP
        # ----------------------------------------------------

        response.raise_for_status()

        # ----------------------------------------------------
        # JSON
        # ----------------------------------------------------

        try:
            data = response.json()

        except ValueError as exc:
            raise KwaiCommentsError(
                "O endpoint Tiny retornou uma resposta "
                "que não é JSON. "
                f"status={response.status_code} "
                f"body={response.text[:500]!r}"
            ) from exc

        if not isinstance(data, dict):
            raise KwaiCommentsError(
                "A resposta Tiny do Kwai "
                "não é um objeto JSON."
            )

        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        result = data.get("result")

        if (
            result is not None
            and result != 1
        ):
            raise KwaiCommentsError(
                "A API Tiny retornou erro. "
                f"result={result!r} "
                f"error_msg={data.get('error_msg')!r}"
            )

        # ----------------------------------------------------
        # COMMENTS
        # ----------------------------------------------------

        comments_raw = data.get("comments")

        if comments_raw is None:
            raise KwaiCommentsError(
                "A resposta Tiny não contém "
                "o campo 'comments'. "
                f"Campos recebidos: "
                f"{sorted(data.keys())}"
            )

        if not isinstance(
            comments_raw,
            list,
        ):
            raise KwaiCommentsError(
                "O campo 'comments' da resposta "
                "Tiny não é uma lista."
            )

        comments: list[dict[str, Any]] = [
            item
            for item in comments_raw
            if isinstance(item, dict)
        ]

        return comments

    except httpx.HTTPStatusError as exc:
        response_preview = (
            exc.response.text[:500]
        )

        raise KwaiCommentsError(
            f"Erro HTTP "
            f"{exc.response.status_code} "
            f"em {TINY_COMMENTS_ENDPOINT}. "
            f"Resposta: "
            f"{response_preview!r}"
        ) from exc

    except httpx.RequestError as exc:
        raise KwaiCommentsError(
            "Erro de conexão com "
            f"o Kwai Tiny: {exc}"
        ) from exc

    finally:
        if owns_client:
            client.close()
# ============================================================
# NORMALIZAÇÃO TINY
# ============================================================


def normalize_tiny_comment(
    comment: dict[str, Any],
) -> dict[str, Any]:
    """
    Normaliza os campos da classe TinyComment encontrada
    dentro do APK.
    """

    return {
        "comment_id": comment.get(
            "commentId"
        ),
        "content": comment.get(
            "content"
        ),
        "user_id": comment.get(
            "userId"
        ),
        "user_name": comment.get(
            "userName"
        ),
        "like_count": comment.get(
            "commentLikeCount",
            0,
        ),
        "comment_time": comment.get(
            "commentTime"
        ),
        "reply_to_comment_id": comment.get(
            "replyToCommentId"
        ),
        "sub_comment_count": comment.get(
            "sub_comment_count",
            0,
        ),
        "is_hot": comment.get(
            "is_hot",
            False,
        ),
        "is_pin": comment.get(
            "is_pin",
            False,
        ),
        "is_amazing": comment.get(
            "is_amazing",
            False,
        ),
        "is_big_fan": comment.get(
            "isBigFan",
            False,
        ),
        "is_friend_comment": comment.get(
            "friendComment",
            False,
        ),
        "is_nearby_author": comment.get(
            "nearbyAuthor",
            False,
        ),
        "recall_type": comment.get(
            "recallType"
        ),
        "user_heads": comment.get(
            "userHeads",
            [],
        ),
        "raw": comment,
    }


def normalize_tiny_comments(
    comments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        normalize_tiny_comment(comment)
        for comment in comments
    ]


# ============================================================
# TODOS OS COMENTÁRIOS WEB / PC
# ============================================================


def get_all_comments(
    photo_id: str,
    *,
    max_comments: int | None = None,
    delay: float = 0.25,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    owns_client = client is None

    if client is None:
        client = create_client()

    comments: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    cursor = ""
    first_page = True

    try:
        while cursor != "no_more":
            root_comment_count = (
                10
                if first_page
                else 20
            )

            page_comments, next_cursor = (
                get_comments(
                    photo_id=photo_id,
                    cursor=cursor,
                    root_comment_count=(
                        root_comment_count
                    ),
                    sub_comment_count=2,
                    client=client,
                )
            )

            new_comments = 0

            for comment in page_comments:
                comment_id = comment.get(
                    "commentId"
                )

                if comment_id is None:
                    comment_id = comment.get(
                        "comment_id"
                    )

                identifier = (
                    str(comment_id)
                    if comment_id is not None
                    else repr(comment)
                )

                if identifier in seen_ids:
                    continue

                seen_ids.add(identifier)
                comments.append(comment)
                new_comments += 1

                if (
                    max_comments is not None
                    and len(comments)
                    >= max_comments
                ):
                    return comments[
                        :max_comments
                    ]

            if next_cursor == "no_more":
                break

            if next_cursor == cursor:
                break

            if (
                not page_comments
                and new_comments == 0
            ):
                break

            cursor = next_cursor
            first_page = False

            if delay > 0:
                sleep(delay)

        return comments

    finally:
        if owns_client:
            client.close()


# ============================================================
# TODOS OS SUBCOMENTÁRIOS WEB / PC
# ============================================================


def get_all_subcomments(
    photo_id: str,
    root_comment: dict[str, Any],
    *,
    max_subcomments: int | None = None,
    delay: float = 0.25,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    root_comment_id = root_comment.get(
        "commentId"
    )

    if root_comment_id is None:
        root_comment_id = root_comment.get(
            "comment_id"
        )

    if root_comment_id is None:
        raise KwaiCommentsError(
            "O comentário principal "
            "não possui commentId."
        )

    owns_client = client is None

    if client is None:
        client = create_client()

    collected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    embedded = root_comment.get(
        "subComments",
        [],
    )

    if isinstance(embedded, list):
        for subcomment in embedded:
            if not isinstance(
                subcomment,
                dict,
            ):
                continue

            sub_id = subcomment.get(
                "commentId"
            )

            if sub_id is None:
                sub_id = subcomment.get(
                    "comment_id"
                )

            identifier = (
                str(sub_id)
                if sub_id is not None
                else repr(subcomment)
            )

            if identifier in seen_ids:
                continue

            seen_ids.add(identifier)
            collected.append(subcomment)

            if (
                max_subcomments is not None
                and len(collected)
                >= max_subcomments
            ):
                return collected[
                    :max_subcomments
                ]

    total_raw = root_comment.get(
        "subCommentCount"
    )

    try:
        total = (
            int(total_raw)
            if total_raw is not None
            else None
        )

    except (TypeError, ValueError):
        total = None

    if (
        total is not None
        and total <= len(collected)
    ):
        return collected

    cursor = ""

    try:
        while cursor != "no_more":
            page, next_cursor = (
                get_subcomments(
                    photo_id=photo_id,
                    root_comment_id=str(
                        root_comment_id
                    ),
                    cursor=cursor,
                    client=client,
                )
            )

            new_items = 0

            for subcomment in page:
                sub_id = subcomment.get(
                    "commentId"
                )

                if sub_id is None:
                    sub_id = subcomment.get(
                        "comment_id"
                    )

                identifier = (
                    str(sub_id)
                    if sub_id is not None
                    else repr(subcomment)
                )

                if identifier in seen_ids:
                    continue

                seen_ids.add(identifier)
                collected.append(
                    subcomment
                )

                new_items += 1

                if (
                    max_subcomments
                    is not None
                    and len(collected)
                    >= max_subcomments
                ):
                    return collected[
                        :max_subcomments
                    ]

            if (
                total is not None
                and len(collected) >= total
            ):
                break

            if next_cursor == "no_more":
                break

            if next_cursor == cursor:
                break

            if (
                not page
                and new_items == 0
            ):
                break

            cursor = next_cursor

            if delay > 0:
                sleep(delay)

        return collected

    finally:
        if owns_client:
            client.close()


# ============================================================
# COMENTÁRIOS + RESPOSTAS WEB / PC
# ============================================================


def get_all_comments_with_replies(
    photo_id: str,
    *,
    max_comments: int | None = None,
    max_subcomments_per_comment: int | None = None,
    delay: float = 0.25,
) -> list[dict[str, Any]]:
    with create_client() as client:
        root_comments = get_all_comments(
            photo_id=photo_id,
            max_comments=max_comments,
            delay=delay,
            client=client,
        )

        complete_comments: list[
            dict[str, Any]
        ] = []

        for root_comment in root_comments:
            result = dict(root_comment)

            total_raw = root_comment.get(
                "subCommentCount",
                0,
            )

            try:
                total_subcomments = int(
                    total_raw or 0
                )

            except (TypeError, ValueError):
                total_subcomments = 0

            if total_subcomments > 0:
                subcomments = (
                    get_all_subcomments(
                        photo_id=photo_id,
                        root_comment=(
                            root_comment
                        ),
                        max_subcomments=(
                            max_subcomments_per_comment
                        ),
                        delay=delay,
                        client=client,
                    )
                )

                result[
                    "subComments"
                ] = subcomments

            complete_comments.append(
                result
            )

        return complete_comments