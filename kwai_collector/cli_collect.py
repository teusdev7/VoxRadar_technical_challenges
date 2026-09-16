import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from typing import Any

import httpx

from kwai_collector.cli_builders import (
    montar_perfil,
    montar_post_fallback,
    montar_tiny_query_params,
    montar_url_post,
)
from kwai_collector.cli_utils import (
    limpar_usuario,
    nome_arquivo_seguro,
    salvar_json,
)
from kwai_collector.clients.comment_client import (
    KwaiCommentsError,
)
from kwai_collector.clients.post_detail_client import (
    KwaiPostError,
)

PostRaw = dict[str, Any]

GetProfilePostsFn = Callable[
    ...,
    list[PostRaw],
]

GetPostDetailsFn = Callable[
    ...,
    dict[str, Any],
]

GetTinyCommentsFn = Callable[
    ...,
    list[PostRaw],
]


def executar_coleta_agregada_com_dependencias(
    perfil_informado: str,
    output_dir: Path,
    delay: float,
    debug: bool,
    *,
    max_posts: int,
    max_comentarios_por_post: int,
    get_all_profile_posts_fn: GetProfilePostsFn,
    get_post_details_fn: GetPostDetailsFn,
    get_tiny_comments_fn: GetTinyCommentsFn,
    logger: logging.Logger,
) -> int:
    try:
        usuario = limpar_usuario(
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
        "Perfil solicitado: %s",
        usuario_consulta,
    )

    logger.info(
        "Buscando os primeiros %d posts...",
        max_posts,
    )

    try:
        posts_encontrados = (
            get_all_profile_posts_fn(
                user_id=usuario_consulta,
                max_paginas=1,
                delay=0.0,
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

    if not posts_encontrados:
        logger.error(
            "Nenhuma postagem encontrada "
            "para o perfil %s.",
            usuario_consulta,
        )
        return 1

    posts_selecionados = (
        posts_encontrados[:max_posts]
    )

    perfil = montar_perfil(
        usuario,
        posts_selecionados,
    )

    logger.info(
        "Perfil identificado: %s (@%s)",
        perfil.get("nome"),
        perfil.get("usuario"),
    )

    logger.info(
        "Posts selecionados: %d",
        len(posts_selecionados),
    )

    posts_saida: list[
        dict[str, object]
    ] = []

    comentarios_por_post: list[
        dict[str, object]
    ] = []

    total_comentarios = 0

    for indice, post in enumerate(
        posts_selecionados,
        start=1,
    ):
        photo_id_valor = post.get(
            "photo_id_str"
        )

        if photo_id_valor is None:
            logger.warning(
                "[%d/%d] Post sem photo_id. "
                "Ignorando.",
                indice,
                len(posts_selecionados),
            )
            continue

        photo_id = str(
            photo_id_valor
        )

        url_post = montar_url_post(
            post
        )

        logger.info(
            "[%d/%d] Processando post %s",
            indice,
            len(posts_selecionados),
            photo_id,
        )

        dados_post = montar_post_fallback(
            post
        )

        erro_detalhes: str | None = None

        if url_post is not None:
            try:
                dados_post = (
                    get_post_details_fn(
                        url_post,
                        expected_photo_id=photo_id,
                    )
                )

            except KwaiPostError as exc:
                erro_detalhes = str(
                    exc
                )

                logger.warning(
                    "[%d/%d] Não foi possível "
                    "obter todos os detalhes "
                    "do post %s: %s",
                    indice,
                    len(posts_selecionados),
                    photo_id,
                    exc,
                )

        if erro_detalhes is not None:
            dados_post[
                "erro_detalhes"
            ] = erro_detalhes

        posts_saida.append(
            dados_post
        )

        comentarios_json: list[
            dict[str, object]
        ] = []

        erro_comentarios: (
            str | None
        ) = None

        try:
            parametros = (
                montar_tiny_query_params()
            )

            comentarios = (
                get_tiny_comments_fn(
                    photo_id=photo_id,
                    query_params=parametros,
                    debug=debug,
                )
            )

            comentarios_json = [
                dict(comentario)
                for comentario in comentarios[
                    :max_comentarios_por_post
                ]
            ]

        except KwaiCommentsError as exc:
            erro_comentarios = str(
                exc
            )

            logger.warning(
                "[%d/%d] Falha ao coletar "
                "comentários do post %s: %s",
                indice,
                len(posts_selecionados),
                photo_id,
                exc,
            )

        quantidade = len(
            comentarios_json
        )

        total_comentarios += (
            quantidade
        )

        registro_comentarios: dict[
            str,
            object,
        ] = {
            "photo_id": photo_id,
            "url": url_post,
            "caption": post.get(
                "caption"
            ),
            "quantidade": quantidade,
            "comentarios": (
                comentarios_json
            ),
        }

        if erro_comentarios is not None:
            registro_comentarios[
                "erro"
            ] = erro_comentarios

        comentarios_por_post.append(
            registro_comentarios
        )

        logger.info(
            "[%d/%d] Comentários coletados: %d",
            indice,
            len(posts_selecionados),
            quantidade,
        )

        if (
            indice
            < len(posts_selecionados)
            and delay > 0
        ):
            sleep(
                delay
            )

    coletado_em = datetime.now(
        UTC
    ).isoformat()

    posts_documento = {
        "perfil": perfil,
        "coletado_em": coletado_em,
        "limite_posts": max_posts,
        "total_posts_coletados": len(
            posts_saida
        ),
        "posts": posts_saida,
    }

    comentarios_documento = {
        "perfil": perfil,
        "coletado_em": coletado_em,
        "limite_posts": max_posts,
        "limite_comentarios_por_post": (
            max_comentarios_por_post
        ),
        "total_posts_processados": len(
            comentarios_por_post
        ),
        "total_comentarios_coletados": (
            total_comentarios
        ),
        "posts": comentarios_por_post,
    }

    nome_base = nome_arquivo_seguro(
        usuario
    )

    arquivo_posts = (
        output_dir
        / f"{nome_base}_posts.json"
    )

    arquivo_comentarios = (
        output_dir
        / f"{nome_base}_comentarios.json"
    )

    salvar_json(
        posts_documento,
        arquivo_posts,
    )

    salvar_json(
        comentarios_documento,
        arquivo_comentarios,
    )

    logger.info(
        "========================================"
    )

    logger.info(
        "Coleta concluída."
    )

    logger.info(
        "Perfil: @%s",
        perfil.get(
            "usuario"
        ),
    )

    logger.info(
        "Posts coletados: %d",
        len(posts_saida),
    )

    logger.info(
        "Comentários coletados: %d",
        total_comentarios,
    )

    logger.info(
        "Posts salvos em: %s",
        arquivo_posts,
    )

    logger.info(
        "Comentários salvos em: %s",
        arquivo_comentarios,
    )

    logger.info(
        "========================================"
    )

    return 0