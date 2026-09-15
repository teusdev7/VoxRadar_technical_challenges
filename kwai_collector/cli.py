import logging
import sys
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
from kwai_collector.cli_normalizers import (
    normalizar_comentarios_com_parser,
    normalizar_posts_com_parser,
)
from kwai_collector.cli_parsers import (
    criar_parser_buscar,
    criar_parser_coletar,
    criar_parser_comentarios,
    criar_parser_legado,
    criar_parser_perfil,
    mostrar_ajuda_principal,
)
from kwai_collector.cli_utils import (
    extrair_photo_id,
    limpar_usuario,
    nome_arquivo_seguro,
    salvar_json,
)
from kwai_collector.clients.comment_client import (
    KwaiCommentsError,
)
from kwai_collector.clients.kwai_client import (
    search_all_posts,
)
from kwai_collector.clients.post_detail_client import (
    KwaiPostError,
    get_post_details,
)
from kwai_collector.clients.profile_client import (
    get_all_profile_posts,
)
from kwai_collector.clients.tiny_comment_client import (
    get_tiny_comments,
)
from kwai_collector.parsers.comment_parser import (
    parse_comment,
)
from kwai_collector.parsers.post_parser import (
    parse_post,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

MAX_POSTS = 10
MAX_COMENTARIOS_POR_POST = 20


def normalizar_posts(
    posts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return normalizar_posts_com_parser(
        posts,
        parse_post,
        logger,
    )


def normalizar_comentarios(
    comentarios: list[dict[str, Any]],
    postagem_url: str,
) -> list[dict[str, Any]]:
    return normalizar_comentarios_com_parser(
        comentarios,
        postagem_url,
        parse_comment,
        logger,
    )


def executar_busca(
    palavra: str,
    output_dir: Path,
    delay: float,
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
        posts_brutos = search_all_posts(
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

    posts = normalizar_posts(
        posts_brutos
    )

    nome = nome_arquivo_seguro(
        palavra
    )

    arquivo_saida = (
        output_dir
        / f"busca_{nome}.json"
    )

    salvar_json(
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


def executar_perfil(
    perfil_informado: str,
    output_dir: Path,
    delay: float,
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
        "Coletando posts do perfil: %s",
        usuario_consulta,
    )

    try:
        posts_brutos = get_all_profile_posts(
            user_id=usuario_consulta,
            delay=delay,
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

    posts = normalizar_posts(
        posts_brutos
    )

    arquivo_saida = (
        output_dir
        / (
            f"{nome_arquivo_seguro(usuario)}"
            "_posts.json"
        )
    )

    salvar_json(
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


def executar_comentarios(
    postagem_url: str,
    output_dir: Path,
    debug: bool,
) -> int:
    try:
        photo_id = extrair_photo_id(
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
            montar_tiny_query_params()
        )

        comentarios_brutos = (
            get_tiny_comments(
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

    comentarios = normalizar_comentarios(
        comentarios_brutos,
        postagem_url,
    )

    arquivo_saida = (
        output_dir
        / f"{photo_id}_comentarios.json"
    )

    salvar_json(
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


def executar_coleta_agregada(
    perfil_informado: str,
    output_dir: Path,
    delay: float,
    debug: bool,
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
        MAX_POSTS,
    )

    try:
        posts_encontrados = (
            get_all_profile_posts(
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
        posts_encontrados[:MAX_POSTS]
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
                dados_post = get_post_details(
                    url_post,
                    expected_photo_id=photo_id,
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
                get_tiny_comments(
                    photo_id=photo_id,
                    query_params=parametros,
                    debug=debug,
                )
            )

            comentarios_json = [
                dict(comentario)
                for comentario
                in comentarios[
                    :MAX_COMENTARIOS_POR_POST
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
        "limite_posts": MAX_POSTS,
        "total_posts_coletados": len(
            posts_saida
        ),
        "posts": posts_saida,
    }

    comentarios_documento = {
        "perfil": perfil,
        "coletado_em": coletado_em,
        "limite_posts": MAX_POSTS,
        "limite_comentarios_por_post": (
            MAX_COMENTARIOS_POR_POST
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


def main(
    argv: list[str] | None = None,
) -> int:
    argumentos = (
        list(sys.argv[1:])
        if argv is None
        else list(argv)
    )

    if not argumentos:
        mostrar_ajuda_principal()
        return 1

    primeiro = argumentos[0]

    if primeiro in (
        "-h",
        "--help",
    ):
        mostrar_ajuda_principal()
        return 0

    if primeiro == "buscar":
        parser = criar_parser_buscar()

        args = parser.parse_args(
            argumentos[1:]
        )

        return executar_busca(
            palavra=args.palavra,
            output_dir=args.output_dir,
            delay=args.delay,
        )

    if primeiro == "perfil":
        parser = criar_parser_perfil()

        args = parser.parse_args(
            argumentos[1:]
        )

        return executar_perfil(
            perfil_informado=args.perfil,
            output_dir=args.output_dir,
            delay=args.delay,
        )

    if primeiro == "comentarios":
        parser = (
            criar_parser_comentarios()
        )

        args = parser.parse_args(
            argumentos[1:]
        )

        return executar_comentarios(
            postagem_url=args.postagem,
            output_dir=args.output_dir,
            debug=args.debug,
        )

    if primeiro == "coletar":
        parser = criar_parser_coletar()

        args = parser.parse_args(
            argumentos[1:]
        )

        return executar_coleta_agregada(
            perfil_informado=args.perfil,
            output_dir=args.output_dir,
            delay=args.delay,
            debug=args.debug,
        )

    parser = criar_parser_legado()

    args = parser.parse_args(
        argumentos
    )

    return executar_coleta_agregada(
        perfil_informado=args.perfil,
        output_dir=args.output_dir,
        delay=args.delay,
        debug=args.debug,
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )