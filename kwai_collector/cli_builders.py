from time import time
from typing import Any


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