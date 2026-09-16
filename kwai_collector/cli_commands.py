import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from kwai_collector.clients.comment_client import (
    KwaiCommentsError,
)

PostRaw = dict[str, Any]

SearchPostsFn = Callable[..., list[PostRaw]]
GetProfilePostsFn = Callable[..., list[PostRaw]]
GetCommentsFn = Callable[..., list[PostRaw]]

NormalizePostsFn = Callable[
    [list[PostRaw]],
    list[dict[str, Any]],
]

NormalizeCommentsFn = Callable[
    [list[PostRaw], str],
    list[dict[str, Any]],
]

SaveJsonFn = Callable[
    [object, Path],
    None,
]

SafeNameFn = Callable[
    [str],
    str,
]

CleanUserFn = Callable[
    [str],
    str,
]

ExtractPhotoIdFn = Callable[
    [str],
    str,
]

QueryParamsFn = Callable[
    [],
    dict[str, str],
]


def executar_busca_com_dependencias(
    palavra: str,
    output_dir: Path,
    delay: float,
    *,
    search_all_posts_fn: SearchPostsFn,
    normalizar_posts_fn: NormalizePostsFn,
    nome_arquivo_seguro_fn: SafeNameFn,
    salvar_json_fn: SaveJsonFn,
    logger: logging.Logger,
) -> int:
    palavra = palavra.strip()

    if not palavra:
        logger.error(
            "Informe uma palavra-chave válida."
        )
        return 1

    logger.info(
        "Buscando posts por: %s",
        palavra,
    )

    try:
        posts_brutos = search_all_posts_fn(
            palavra,
            delay=delay,
        )

    except (
        httpx.RequestError,
        httpx.HTTPStatusError,
        RuntimeError,
    ) as exc:
        logger.error(
            "Falha ao buscar posts: %s",
            exc,
        )
        return 1

    posts = normalizar_posts_fn(
        posts_brutos
    )

    nome = nome_arquivo_seguro_fn(
        palavra
    )

    arquivo_saida = (
        output_dir
        / f"busca_{nome}.json"
    )

    salvar_json_fn(
        posts,
        arquivo_saida,
    )

    logger.info(
        "Busca concluída."
    )

    logger.info(
        "Posts coletados: %d",
        len(posts),
    )

    logger.info(
        "Arquivo salvo em: %s",
        arquivo_saida,
    )

    return 0


def executar_perfil_com_dependencias(
    perfil_informado: str,
    output_dir: Path,
    delay: float,
    *,
    limpar_usuario_fn: CleanUserFn,
    get_all_profile_posts_fn: GetProfilePostsFn,
    normalizar_posts_fn: NormalizePostsFn,
    nome_arquivo_seguro_fn: SafeNameFn,
    salvar_json_fn: SaveJsonFn,
    logger: logging.Logger,
) -> int:
    try:
        usuario = limpar_usuario_fn(
            perfil_informado
        )

    except ValueError as exc:
        logger.error(
            "%s",
            exc,
        )
        return 1

    usuario_consulta = (
        f"@{usuario}"
    )

    logger.info(
        "Coletando posts do perfil: %s",
        usuario_consulta,
    )

    try:
        posts_brutos = (
            get_all_profile_posts_fn(
                user_id=usuario_consulta,
                delay=delay,
            )
        )

    except (
        httpx.RequestError,
        httpx.HTTPStatusError,
        RuntimeError,
    ) as exc:
        logger.error(
            "Falha ao coletar o perfil: %s",
            exc,
        )
        return 1

    if not posts_brutos:
        logger.error(
            "Nenhuma postagem encontrada "
            "para o perfil %s.",
            usuario_consulta,
        )
        return 1

    posts = normalizar_posts_fn(
        posts_brutos
    )

    arquivo_saida = (
        output_dir
        / (
            f"{nome_arquivo_seguro_fn(usuario)}"
            "_posts.json"
        )
    )

    salvar_json_fn(
        posts,
        arquivo_saida,
    )

    logger.info(
        "Coleta do perfil concluída."
    )

    logger.info(
        "Posts coletados: %d",
        len(posts),
    )

    logger.info(
        "Arquivo salvo em: %s",
        arquivo_saida,
    )

    return 0


def executar_comentarios_com_dependencias(
    postagem_url: str,
    output_dir: Path,
    debug: bool,
    *,
    extrair_photo_id_fn: ExtractPhotoIdFn,
    montar_tiny_query_params_fn: QueryParamsFn,
    get_tiny_comments_fn: GetCommentsFn,
    normalizar_comentarios_fn: NormalizeCommentsFn,
    salvar_json_fn: SaveJsonFn,
    logger: logging.Logger,
) -> int:
    try:
        photo_id = extrair_photo_id_fn(
            postagem_url
        )

    except ValueError as exc:
        logger.error(
            "%s",
            exc,
        )
        return 1

    logger.info(
        "Coletando comentários do post %s",
        photo_id,
    )

    try:
        parametros = (
            montar_tiny_query_params_fn()
        )

        comentarios_brutos = (
            get_tiny_comments_fn(
                photo_id=photo_id,
                query_params=parametros,
                debug=debug,
            )
        )

    except KwaiCommentsError as exc:
        logger.error(
            "Falha ao coletar comentários: %s",
            exc,
        )
        return 1

    comentarios = (
        normalizar_comentarios_fn(
            comentarios_brutos,
            postagem_url,
        )
    )

    arquivo_saida = (
        output_dir
        / f"{photo_id}_comentarios.json"
    )

    salvar_json_fn(
        comentarios,
        arquivo_saida,
    )

    logger.info(
        "Coleta de comentários concluída."
    )

    logger.info(
        "Comentários coletados: %d",
        len(comentarios),
    )

    logger.info(
        "Arquivo salvo em: %s",
        arquivo_saida,
    )

    return 0