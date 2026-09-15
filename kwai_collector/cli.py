import argparse
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from time import sleep, time
from typing import Any

import httpx

from kwai_collector.clients.comment_client import (
    KwaiCommentsError,
    get_tiny_comments,
)
from kwai_collector.clients.post_detail_client import (
    KwaiPostError,
    get_post_details,
)
from kwai_collector.clients.profile_client import (
    get_all_profile_posts,
)
from kwai_collector.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

MAX_POSTS = 10
MAX_COMENTARIOS_POR_POST = 20


def numero_nao_negativo(value: str) -> float:
    numero = float(value)

    if numero < 0:
        raise argparse.ArgumentTypeError(
            "não pode ser um número negativo."
        )

    return numero


def salvar_json(
    dados: object,
    arquivo_saida: Path,
) -> None:
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


def limpar_usuario(
    usuario: str,
) -> str:
    usuario = (
        usuario
        .strip()
        .removeprefix("@")
    )

    if not usuario:
        raise ValueError(
            "Informe um perfil válido."
        )

    return usuario


def nome_arquivo_seguro(
    usuario: str,
) -> str:
    nome = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        usuario,
    )

    return nome.strip(
        "._-"
    ) or "perfil"


def montar_tiny_query_params() -> dict[str, str]:
    timestamp = str(
        int(time() * 1000)
    )

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


def montar_url_post(
    post: dict[str, Any],
) -> str | None:
    photo_id = post.get(
        "photo_id_str"
    )

    kwai_id = post.get(
        "kwai_id"
    )

    if not photo_id or not kwai_id:
        return None

    return (
        "https://www.kwai.com/"
        f"@{kwai_id}/video/{photo_id}"
    )


def primeiro_url(
    valor: object,
) -> str | None:
    if not isinstance(
        valor,
        list,
    ):
        return None

    for item in valor:
        if not isinstance(
            item,
            dict,
        ):
            continue

        url = item.get(
            "url"
        )

        if isinstance(
            url,
            str,
        ):
            return url

    return None


def montar_perfil(
    usuario_solicitado: str,
    posts: list[dict[str, Any]],
) -> dict[str, object]:
    primeiro_post = posts[0]

    kwai_id = primeiro_post.get(
        "kwai_id"
    )

    if not isinstance(
        kwai_id,
        str,
    ):
        kwai_id = usuario_solicitado

    nome = primeiro_post.get(
        "user_name"
    )

    user_id = primeiro_post.get(
        "user_id_str"
    )

    bio = primeiro_post.get(
        "user_text"
    )

    verificado = primeiro_post.get(
        "verified"
    )

    avatar = primeiro_url(
        primeiro_post.get(
            "headurls"
        )
    )

    return {
        "usuario": kwai_id,
        "nome": nome,
        "id": user_id,
        "bio": bio,
        "verificado": verificado,
        "avatar": avatar,
        "url": (
            "https://www.kwai.com/"
            f"@{kwai_id}"
        ),
    }


def montar_post_fallback(
    post: dict[str, Any],
) -> dict[str, object]:
    photo_id = post.get(
        "photo_id_str"
    )

    kwai_id = post.get(
        "kwai_id"
    )

    url_post = montar_url_post(
        post
    )

    url_perfil: str | None = None

    if isinstance(
        kwai_id,
        str,
    ):
        url_perfil = (
            "https://www.kwai.com/"
            f"@{kwai_id}"
        )

    thumbnail = primeiro_url(
        post.get(
            "cover_thumbnail_urls"
        )
    )

    if thumbnail is None:
        thumbnail = primeiro_url(
            post.get(
                "cover_first_frame_urls"
            )
        )

    return {
        "photo_id": (
            str(photo_id)
            if photo_id is not None
            else None
        ),
        "url": url_post,
        "autor": {
            "nome": post.get(
                "user_name"
            ),
            "usuario": kwai_id,
            "id": post.get(
                "user_id_str"
            ),
            "url_perfil": url_perfil,
        },
        "caption": post.get(
            "caption"
        ),
        "descricao": None,
        "publicado_em": None,
        "data_original": post.get(
            "time"
        ),
        "timestamp": post.get(
            "timestamp"
        ),
        "duracao": None,
        "thumbnail": thumbnail,
        "engajamento": {
            "curtidas": post.get(
                "like_count"
            ),
            "comentarios": post.get(
                "comment_count"
            ),
            "compartilhamentos": post.get(
                "forward_count"
            ),
            "visualizacoes": post.get(
                "view_count"
            ),
            "curtidas_seo": None,
            "comentarios_seo": None,
        },
    }


parser = argparse.ArgumentParser(
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


def main(
    argv: list[str] | None = None,
) -> int:
    args = parser.parse_args(
        argv
    )

    try:
        usuario = limpar_usuario(
            args.perfil
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
                dados_post = (
                    get_post_details(
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

        erro_comentarios: str | None = None

        try:
            parametros = (
                montar_tiny_query_params()
            )

            comentarios = (
                get_tiny_comments(
                    photo_id=photo_id,
                    query_params=parametros,
                    debug=args.debug,
                )
            )

            comentarios_json = [
                dict(comentario)
                for comentario in comentarios[
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
            "comentarios": comentarios_json,
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
            and args.delay > 0
        ):
            sleep(
                args.delay
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
        args.output_dir
        / f"{nome_base}_posts.json"
    )

    arquivo_comentarios = (
        args.output_dir
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


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
