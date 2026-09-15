import json

from kwai_collector import cli
from kwai_collector.cli import main


def criar_post(
    indice: int,
) -> dict[str, object]:
    photo_id = (
        f"52535990778134066{indice:02d}"
    )

    return {
        "kwai_id": "perfil_teste",
        "photo_id_str": photo_id,
        "user_name": "Perfil Teste",
        "user_id_str": "123456",
        "user_text": "Bio do perfil",
        "verified": False,
        "caption": f"Post {indice}",
        "time": "2026-09-14 12:00:00",
        "timestamp": 1789400000000 + indice,
        "like_count": 100 + indice,
        "comment_count": 30,
        "forward_count": 5,
        "view_count": 1000 + indice,
        "headurls": [
            {
                "url": (
                    "https://example.com/"
                    "avatar.jpg"
                )
            }
        ],
        "cover_thumbnail_urls": [
            {
                "url": (
                    "https://example.com/"
                    f"capa-{indice}.jpg"
                )
            }
        ],
    }


def test_cli_coleta_10_posts_e_comentarios(
    monkeypatch,
    tmp_path,
):
    posts = [
        criar_post(indice)
        for indice in range(12)
    ]

    def fake_get_all_profile_posts(
        user_id,
        max_paginas=1,
        delay=0.0,
    ):
        assert user_id == "@perfil_teste"
        assert max_paginas == 1
        assert delay == 0.0

        return posts

    chamadas_detalhes: list[str] = []

    def fake_get_post_details(
        url,
        expected_photo_id=None,
    ):
        assert expected_photo_id is not None

        chamadas_detalhes.append(
            expected_photo_id
        )

        return {
            "photo_id": expected_photo_id,
            "url": url,
            "autor": {
                "nome": "Perfil Teste",
                "usuario": "perfil_teste",
                "id": "123456",
                "url_perfil": (
                    "https://www.kwai.com/"
                    "@perfil_teste"
                ),
            },
            "caption": "Post de teste",
            "descricao": "Descrição",
            "publicado_em": (
                "2026-09-14T12:00:00Z"
            ),
            "data_original": (
                "2026-09-14 12:00:00"
            ),
            "timestamp": 1789400000000,
            "duracao": "PT1M",
            "thumbnail": (
                "https://example.com/"
                "capa.jpg"
            ),
            "engajamento": {
                "curtidas": 100,
                "comentarios": 30,
                "compartilhamentos": 5,
                "visualizacoes": 1000,
                "curtidas_seo": None,
                "comentarios_seo": None,
            },
        }

    chamadas_comentarios: list[str] = []

    def fake_get_tiny_comments(
        photo_id,
        query_params=None,
        debug=False,
    ):
        chamadas_comentarios.append(
            photo_id
        )

        return [
            {
                "commentId": indice,
                "userName": (
                    f"Usuario {indice}"
                ),
                "kwaiid": (
                    f"usuario{indice}"
                ),
                "content": (
                    f"Comentario {indice}"
                ),
                "commentLikeCount": indice,
            }
            for indice in range(20)
        ]

    monkeypatch.setattr(
        cli,
        "get_all_profile_posts",
        fake_get_all_profile_posts,
    )

    monkeypatch.setattr(
        cli,
        "get_post_details",
        fake_get_post_details,
    )

    monkeypatch.setattr(
        cli,
        "get_tiny_comments",
        fake_get_tiny_comments,
    )

    codigo = main(
        [
            "@perfil_teste",
            "--output-dir",
            str(tmp_path),
            "--delay",
            "0",
        ]
    )

    assert codigo == 0

    arquivo_posts = (
        tmp_path
        / "perfil_teste_posts.json"
    )

    arquivo_comentarios = (
        tmp_path
        / "perfil_teste_comentarios.json"
    )

    assert arquivo_posts.exists()
    assert arquivo_comentarios.exists()

    dados_posts = json.loads(
        arquivo_posts.read_text(
            encoding="utf-8"
        )
    )

    dados_comentarios = json.loads(
        arquivo_comentarios.read_text(
            encoding="utf-8"
        )
    )

    assert (
        dados_posts[
            "total_posts_coletados"
        ]
        == 10
    )

    assert len(
        dados_posts["posts"]
    ) == 10

    assert (
        dados_comentarios[
            "total_posts_processados"
        ]
        == 10
    )

    assert (
        dados_comentarios[
            "total_comentarios_coletados"
        ]
        == 200
    )

    assert len(
        chamadas_detalhes
    ) == 10

    assert len(
        chamadas_comentarios
    ) == 10

    for post in (
        dados_comentarios["posts"]
    ):
        assert (
            post["quantidade"]
            == 20
        )

        assert len(
            post["comentarios"]
        ) == 20


def test_cli_sem_posts_retorna_erro(
    monkeypatch,
    tmp_path,
):
    def fake_get_all_profile_posts(
        user_id,
        max_paginas=1,
        delay=0.0,
    ):
        return []

    monkeypatch.setattr(
        cli,
        "get_all_profile_posts",
        fake_get_all_profile_posts,
    )

    codigo = main(
        [
            "@perfil_vazio",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert codigo == 1