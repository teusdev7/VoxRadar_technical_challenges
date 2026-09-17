import argparse
import sys
from pathlib import Path

from kwai_collector.cli_utils import (
    numero_nao_negativo,
)
from kwai_collector.config import settings


def criar_parser_legado() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kwai-collector",
        description=(
            "Coleta os 10 primeiros posts públicos "
            "de um perfil do Kwai e até 20 comentários "
            "por postagem."
        ),
    )

    parser.add_argument(
        "perfil",
        help=(
            "Perfil do Kwai. "
            "Exemplo: @ftvfilmeseseri645"
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("samples"),
        help=(
            "Diretório onde os arquivos JSON "
            "serão salvos"
        ),
    )

    parser.add_argument(
        "--delay",
        type=numero_nao_negativo,
        default=settings.delay,
        help=(
            "Intervalo em segundos entre "
            "o processamento dos posts"
        ),
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help=(
            "Exibir informações adicionais "
            "das requisições de comentários"
        ),
    )

    return parser


def criar_parser_buscar() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kwai-collector buscar",
        description=(
            "Busca postagens públicas do Kwai "
            "por palavra-chave."
        ),
    )

    parser.add_argument(
        "palavra",
        help="Palavra-chave da busca.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("samples"),
    )

    parser.add_argument(
        "--delay",
        type=numero_nao_negativo,
        default=settings.delay,
    )

    return parser


def criar_parser_perfil() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kwai-collector perfil",
        description=(
            "Coleta postagens públicas "
            "de um perfil do Kwai."
        ),
    )

    parser.add_argument(
        "perfil",
        help=(
            "Perfil do Kwai. "
            "Exemplo: @usuario"
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("samples"),
    )

    parser.add_argument(
        "--delay",
        type=numero_nao_negativo,
        default=settings.delay,
    )

    return parser


def criar_parser_comentarios() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kwai-collector comentarios",
        description=(
            "Coleta comentários públicos "
            "de uma postagem do Kwai."
        ),
    )

    parser.add_argument(
        "postagem",
        help="URL da postagem ou photo_id.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("samples"),
    )

    parser.add_argument(
        "--debug",
        action="store_true",
    )

    return parser


def criar_parser_coletar() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kwai-collector coletar",
        description=(
            "Coleta os 10 primeiros posts "
            "de um perfil e até 20 comentários "
            "por postagem."
        ),
    )

    parser.add_argument(
        "perfil",
        help=(
            "Perfil do Kwai. "
            "Exemplo: @usuario"
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("samples"),
    )

    parser.add_argument(
        "--delay",
        type=numero_nao_negativo,
        default=settings.delay,
    )

    parser.add_argument(
        "--debug",
        action="store_true",
    )

    return parser


def mostrar_ajuda_principal() -> None:
    mensagem = """
Uso:
  kwai-collector buscar <palavra>
  kwai-collector perfil <@usuario>
  kwai-collector comentarios <url-do-post>
  kwai-collector coletar <@usuario>

Compatibilidade:
  kwai-collector <@usuario>

Comandos:
  buscar        Busca posts por palavra-chave.
  perfil        Coleta posts públicos de um perfil.
  comentarios   Coleta comentários de uma postagem.
  coletar       Coleta 10 posts e até 20 comentários por post.

Use:
  kwai-collector <comando> --help
para ver as opções de cada comando.
""".strip()

    sys.stdout.write(
        f"{mensagem}\n"
    )