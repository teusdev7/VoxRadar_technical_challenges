import logging
import sys
from pathlib import Path
from typing import Any

from kwai_collector.cli_builders import (
    montar_tiny_query_params,
)
from kwai_collector.cli_collect import (
    executar_coleta_agregada_com_dependencias,
)
from kwai_collector.cli_commands import (
    executar_busca_com_dependencias,
    executar_comentarios_com_dependencias,
    executar_perfil_com_dependencias,
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
from kwai_collector.clients.kwai_client import (
    search_all_posts,
)
from kwai_collector.clients.post_detail_client import (
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
    return executar_busca_com_dependencias(
        palavra,
        output_dir,
        delay,
        search_all_posts_fn=search_all_posts,
        normalizar_posts_fn=normalizar_posts,
        nome_arquivo_seguro_fn=nome_arquivo_seguro,
        salvar_json_fn=salvar_json,
        logger=logger,
    )


def executar_perfil(
    perfil_informado: str,
    output_dir: Path,
    delay: float,
) -> int:
    return executar_perfil_com_dependencias(
        perfil_informado,
        output_dir,
        delay,
        limpar_usuario_fn=limpar_usuario,
        get_all_profile_posts_fn=get_all_profile_posts,
        normalizar_posts_fn=normalizar_posts,
        nome_arquivo_seguro_fn=nome_arquivo_seguro,
        salvar_json_fn=salvar_json,
        logger=logger,
    )


def executar_comentarios(
    postagem_url: str,
    output_dir: Path,
    debug: bool,
) -> int:
    return executar_comentarios_com_dependencias(
        postagem_url,
        output_dir,
        debug,
        extrair_photo_id_fn=extrair_photo_id,
        montar_tiny_query_params_fn=(
            montar_tiny_query_params
        ),
        get_tiny_comments_fn=get_tiny_comments,
        normalizar_comentarios_fn=(
            normalizar_comentarios
        ),
        salvar_json_fn=salvar_json,
        logger=logger,
    )


def executar_coleta_agregada(
    perfil_informado: str,
    output_dir: Path,
    delay: float,
    debug: bool,
) -> int:
    return executar_coleta_agregada_com_dependencias(
        perfil_informado,
        output_dir,
        delay,
        debug,
        max_posts=MAX_POSTS,
        max_comentarios_por_post=(
            MAX_COMENTARIOS_POR_POST
        ),
        get_all_profile_posts_fn=(
            get_all_profile_posts
        ),
        get_post_details_fn=get_post_details,
        get_tiny_comments_fn=get_tiny_comments,
        logger=logger,
    )


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