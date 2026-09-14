import argparse
import json
import logging
from pathlib import Path

from kwai_collector.clients.kwai_client import search_all_posts
from kwai_collector.clients.profile_client import get_all_profile_posts
from kwai_collector.config import settings
from kwai_collector.parsers.post_parser import parse_post
from kwai_collector.providers.adb_comment_provider import AdbCommentProvider
from kwai_collector.providers.comment_provider import (
    CommentProvider,
    XmlCommentProvider,
)
from kwai_collector.providers.mobile_comment_provider import (
    MobileCommentProvider,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def numero_positivo(value: str) -> int:
    numero = int(value)

    if numero < 1:
        raise argparse.ArgumentTypeError(
            "não é um número positivo válido."
        )

    return numero


def numero_nao_negativo(value: str) -> float:
    numero = float(value)

    if numero < 0:
        raise argparse.ArgumentTypeError(
            "não pode ser um número negativo."
        )

    return numero


parser = argparse.ArgumentParser(
    description="Coletor de dados do Kwai",
)

subparsers = parser.add_subparsers(
    dest="comando",
    required=True,
)


buscar_parser = subparsers.add_parser(
    "buscar",
    help="Buscar posts no Kwai com base em uma palavra-chave",
)

buscar_parser.add_argument(
    "keyword",
    help="Palavra-chave para buscar no Kwai",
)

buscar_parser.add_argument(
    "--paginas",
    type=numero_positivo,
    default=1,
    help="Número máximo de páginas a serem buscadas",
)

buscar_parser.add_argument(
    "--output",
    type=Path,
    default=Path("samples/busca_cli.json"),
    help="Caminho do arquivo de saída para salvar os resultados",
)

buscar_parser.add_argument(
    "--delay",
    type=numero_nao_negativo,
    default=settings.delay,
    help="Atraso em segundos entre as requisições",
)


comentarios_parser = subparsers.add_parser(
    "comentarios",
    help="Extrair comentários de uma postagem do Kwai",
)

comentarios_parser.add_argument(
    "url",
    help="URL da postagem do Kwai para extrair comentários",
)

comentarios_source = comentarios_parser.add_mutually_exclusive_group()

comentarios_source.add_argument(
    "--xml",
    type=Path,
    help="Arquivo XML capturado da interface do Kwai",
)

comentarios_source.add_argument(
    "--mobile-json",
    type=Path,
    help="Arquivo JSON capturado do fluxo mobile do Kwai",
)

comentarios_parser.add_argument(
    "--output",
    type=Path,
    default=Path("samples/comentarios_cli.json"),
    help="Caminho do arquivo de saída para salvar os comentários extraídos",
)


perfil_parser = subparsers.add_parser(
    "perfil",
    help="Coletar postagens de um perfil do Kwai",
)

perfil_parser.add_argument(
    "usuario",
    help="Usuário do Kwai, por exemplo @betrobort",
)

perfil_parser.add_argument(
    "--delay",
    type=numero_nao_negativo,
    default=settings.delay,
    help="Atraso em segundos entre as páginas",
)

perfil_parser.add_argument(
    "--paginas",
    type=numero_positivo,
    default=1,
    help="Número máximo de páginas do perfil",
)

perfil_parser.add_argument(
    "--output",
    type=Path,
    default=Path("samples/perfil_cli.json"),
    help="Arquivo JSON de saída",
)


def main(argv: list[str] | None = None) -> int:
    args = parser.parse_args(argv)

    if args.comando == "buscar":
        posts = search_all_posts(
            args.keyword,
            max_paginas=args.paginas,
            delay=args.delay,
        )

        logger.info(
            "Total de posts encontrados: %d",
            len(posts),
        )

        resultados = []

        for post in posts:
            postagem = parse_post(post)
            resultados.append(postagem)

        dados_saida = [
            postagem.model_dump(mode="json")
            for postagem in resultados
        ]

        arquivo_saida = args.output

        arquivo_saida.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with arquivo_saida.open(
            "w",
            encoding="utf-8",
        ) as arquivo:
            json.dump(
                dados_saida,
                arquivo,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(
            "Resultados gerados em: %s",
            arquivo_saida,
        )

        logger.info(
            "Execução concluída com sucesso.",
        )

    elif args.comando == "comentarios":
        provider: CommentProvider

        if args.mobile_json is not None:
            provider = MobileCommentProvider(
                arquivo_json=args.mobile_json,
            )

        elif args.xml is not None:
            provider = XmlCommentProvider(
                arquivo_xml=args.xml,
            )

        else:
            provider = AdbCommentProvider()

        comentarios = provider.get_comments(
            postagem_url=args.url,
        )

        dados_saida = [
            comentario.model_dump(mode="json")
            for comentario in comentarios
        ]

        arquivo_saida = args.output

        arquivo_saida.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with arquivo_saida.open(
            "w",
            encoding="utf-8",
        ) as arquivo:
            json.dump(
                dados_saida,
                arquivo,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(
            "Total de comentários extraídos: %d",
            len(comentarios),
        )

        logger.info(
            "Resultados gerados em: %s",
            arquivo_saida,
        )

        logger.info(
            "Execução concluída com sucesso.",
        )

    elif args.comando == "perfil":
        posts = get_all_profile_posts(
            user_id=args.usuario,
            max_paginas=args.paginas,
            delay=args.delay,
        )

        resultados = []

        for post in posts:
            postagem = parse_post(post)
            resultados.append(postagem)

        dados_saida = [
            postagem.model_dump(mode="json")
            for postagem in resultados
        ]

        arquivo_saida = args.output

        arquivo_saida.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with arquivo_saida.open(
            "w",
            encoding="utf-8",
        ) as arquivo:
            json.dump(
                dados_saida,
                arquivo,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(
            "Total de posts do perfil encontrados: %d",
            len(resultados),
        )

        logger.info(
            "Resultados gerados em: %s",
            arquivo_saida,
        )

        logger.info(
            "Execução concluída com sucesso.",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())