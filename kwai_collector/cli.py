import argparse
import json
import logging
from pathlib import Path
from time import time
from urllib.parse import parse_qs, unquote, urlparse

from kwai_collector.clients.comment_client import (
    KwaiCommentsError,
    get_tiny_comments,
)
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


def extrair_photo_id(valor: str) -> str:
    """
    Extrai o photo_id de uma URL do Kwai.

    Também aceita o photo_id diretamente.
    """

    valor = valor.strip()

    # Permite passar somente o ID.
    if valor.isdigit():
        return valor

    parsed = urlparse(valor)

    # ---------------------------------------------------------
    # Tenta obter pelo query parameter.
    #
    # Exemplo:
    # ?photoId=5253599077813406650
    # ---------------------------------------------------------
    query = parse_qs(parsed.query)

    for chave in ("photoId", "photo_id"):
        valores = query.get(chave)

        if valores:
            photo_id = valores[0].strip()

            if photo_id.isdigit():
                return photo_id

    # ---------------------------------------------------------
    # Tenta obter pelo caminho da URL.
    #
    # Exemplo:
    # /photo/150001691804174/5253599077813406650
    # ---------------------------------------------------------
    partes = [
        unquote(parte)
        for parte in parsed.path.split("/")
        if parte
    ]

    for marcador in ("photo", "video"):
        if marcador not in partes:
            continue

        indice = partes.index(marcador)

        candidatos = partes[indice + 1 :]

        # No formato /photo/user_id/photo_id,
        # o photo_id normalmente é o último número.
        for candidato in reversed(candidatos):
            if candidato.isdigit():
                return candidato

    raise ValueError(
        "Não foi possível encontrar um photo_id válido "
        "na URL informada."
    )


def montar_tiny_query_params() -> dict[str, str]:
    """
    Monta os parâmetros necessários para a Tiny API.

    Estes valores correspondem ao ambiente que validamos
    durante os testes do endpoint de comentários.
    """

    timestamp = str(int(time() * 1000))

    return {
        "ver": "13.7",
        "appver": "13.7.50.646302",
        "pkg": "com.kwai.video",
        "c": "GOOGLE_PLAY",
        "app": "1",
        "os": "android",
        "client_key": "3c2cd3f3",
        "kpn": "KWAI",
        "kpf": "ANDROID_PHONE",
        "kwai_tiny_type": "2",
        "sys": "KWAI_ANDROID_14",
        "mod": "samsung(SM-A356E)",
        "net": "WIFI",
        "language": "pt-br",
        "country_code": "br",
        "mcc": "724",
        "time_zone": (
            "Brasilia Standard Time "
            "America/Sao_Paulo"
        ),
        "ds": "-1",
        "egid": "",
        "abi": "arm64-v8a",
        "timestamp": timestamp,
    }


def salvar_json(
    dados: object,
    arquivo_saida: Path,
) -> None:
    """
    Salva um objeto serializável em JSON.
    """

    arquivo_saida.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with arquivo_saida.open(
        "w",
        encoding="utf-8",
    ) as arquivo:
        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# PARSER PRINCIPAL
# ============================================================

parser = argparse.ArgumentParser(
    description="Coletor de dados do Kwai",
)

subparsers = parser.add_subparsers(
    dest="comando",
    required=True,
)


# ============================================================
# BUSCAR
# ============================================================

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
    help="Caminho do arquivo de saída",
)

buscar_parser.add_argument(
    "--delay",
    type=numero_nao_negativo,
    default=settings.delay,
    help="Atraso em segundos entre as requisições",
)


# ============================================================
# COMMENTS
#
# NOVO FLUXO:
# link -> photo_id -> Tiny API -> até 20 comentários
#
# Não depende do celular conectado.
# ============================================================

comments_parser = subparsers.add_parser(
    "comments",
    help=(
        "Coletar até 20 comentários de uma postagem "
        "usando a Tiny API"
    ),
)

comments_parser.add_argument(
    "url",
    help=(
        "URL da postagem do Kwai ou um photo_id "
        "numérico"
    ),
)

comments_parser.add_argument(
    "--output",
    type=Path,
    default=Path("samples/comentarios_tiny.json"),
    help="Arquivo JSON de saída",
)

comments_parser.add_argument(
    "--debug",
    action="store_true",
    help="Exibir detalhes da requisição HTTP",
)


# ============================================================
# COMENTARIOS
#
# FLUXO ANTIGO:
# ADB / XML / JSON mobile
#
# Mantido para não quebrar funcionalidades anteriores.
# ============================================================

comentarios_parser = subparsers.add_parser(
    "comentarios",
    help="Extrair comentários de uma postagem do Kwai",
)

comentarios_parser.add_argument(
    "url",
    help="URL da postagem do Kwai",
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
    help="Arquivo JSON de saída",
)


# ============================================================
# PERFIL
# ============================================================

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


# ============================================================
# MAIN
# ============================================================


def main(argv: list[str] | None = None) -> int:
    args = parser.parse_args(argv)

    # ========================================================
    # BUSCAR
    # ========================================================

    if args.comando == "buscar":
        posts_busca = search_all_posts(
            args.keyword,
            max_paginas=args.paginas,
            delay=args.delay,
        )

        logger.info(
            "Total de posts encontrados: %d",
            len(posts_busca),
        )

        postagens_busca = []

        for post in posts_busca:
            postagem = parse_post(post)

            postagens_busca.append(
                postagem
            )

        dados_busca = [
            postagem.model_dump(mode="json")
            for postagem in postagens_busca
        ]

        arquivo_busca = args.output

        salvar_json(
            dados_busca,
            arquivo_busca,
        )

        logger.info(
            "Resultados gerados em: %s",
            arquivo_busca,
        )

        logger.info(
            "Execução concluída com sucesso.",
        )

    # ========================================================
    # COMMENTS - TINY API
    # ========================================================

    elif args.comando == "comments":
        try:
            photo_id = extrair_photo_id(
                args.url,
            )

        except ValueError as exc:
            logger.error(
                "%s",
                exc,
            )

            return 1

        logger.info(
            "Photo ID identificado: %s",
            photo_id,
        )

        tiny_query_params = montar_tiny_query_params()

        try:
            comentarios_tiny = get_tiny_comments(
                photo_id=photo_id,
                query_params=tiny_query_params,
                debug=args.debug,
            )

        except KwaiCommentsError as exc:
            logger.error(
                "Falha ao coletar comentários: %s",
                exc,
            )

            return 1

        dados_tiny: list[dict[str, object]] = [
            dict(comentario)
            for comentario in comentarios_tiny
        ]

        arquivo_tiny = args.output

        salvar_json(
            dados_tiny,
            arquivo_tiny,
        )

        logger.info(
            "Total de comentários extraídos: %d",
            len(dados_tiny),
        )

        # Mostra os comentários no terminal.
        for indice, comentario in enumerate(
            dados_tiny,
            start=1,
        ):
            usuario = comentario.get(
                "userName",
                "Usuário desconhecido",
            )

            conteudo = comentario.get(
                "content",
                "",
            )

            logger.info(
                "%02d. %s: %s",
                indice,
                usuario,
                conteudo,
            )

        logger.info(
            "Resultados gerados em: %s",
            arquivo_tiny,
        )

        logger.info(
            "Execução concluída com sucesso.",
        )

    # ========================================================
    # COMENTARIOS - FLUXO ANTIGO
    # ========================================================

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

        comentarios_legados = provider.get_comments(
            postagem_url=args.url,
        )

        dados_comentarios = [
            comentario.model_dump(mode="json")
            for comentario in comentarios_legados
        ]

        arquivo_comentarios = args.output

        salvar_json(
            dados_comentarios,
            arquivo_comentarios,
        )

        logger.info(
            "Total de comentários extraídos: %d",
            len(comentarios_legados),
        )

        logger.info(
            "Resultados gerados em: %s",
            arquivo_comentarios,
        )

        logger.info(
            "Execução concluída com sucesso.",
        )

    # ========================================================
    # PERFIL
    # ========================================================

    elif args.comando == "perfil":
        posts_perfil = get_all_profile_posts(
            user_id=args.usuario,
            max_paginas=args.paginas,
            delay=args.delay,
        )

        postagens_perfil = []

        for post in posts_perfil:
            postagem = parse_post(post)

            postagens_perfil.append(
                postagem
            )

        dados_perfil = [
            postagem.model_dump(mode="json")
            for postagem in postagens_perfil
        ]

        arquivo_perfil = args.output

        salvar_json(
            dados_perfil,
            arquivo_perfil,
        )

        logger.info(
            "Total de posts do perfil encontrados: %d",
            len(postagens_perfil),
        )

        logger.info(
            "Resultados gerados em: %s",
            arquivo_perfil,
        )

        logger.info(
            "Execução concluída com sucesso.",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())