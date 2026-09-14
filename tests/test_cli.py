import json

import pytest

from kwai_collector import cli
from kwai_collector.cli import main
from kwai_collector.clients import kwai_client


def test_cli_rejeita_pagina_zero():
    with pytest.raises(SystemExit) as erro:
        main(
            [
                "buscar",
                "futebol",
                "--paginas",
                "0",
            ]
        )
    assert erro.value.code == 2


def test_cli_buscar_gera_json(monkeypatch, tmp_path):
    def fake_search_all_posts(keyword, max_paginas=5, delay=0.0):
        assert keyword == "futebol"
        assert max_paginas == 2
        return [
            {
                "kwai_id": "usuario_teste",
                "photo_id_str": "123456",
                "user_name": "Usuario Teste",
                "user_id_str": "987654",
                "caption": "Post de teste",
                "time": "2024-10-03 06:42:01",
                "like_count": 100,
                "comment_count": 20,
                "forward_count": 5,
                "view_count": 1000,
            },
        ]

    monkeypatch.setattr(
        cli,
        "search_all_posts",
        fake_search_all_posts,
    )

    arquivo_saida = tmp_path / "resultado.json"

    resultado = main(
        [
            "buscar",
            "futebol",
            "--paginas",
            "2",
            "--output",
            str(arquivo_saida),
        ]
    )

    assert resultado == 0
    assert arquivo_saida.exists()

    with arquivo_saida.open("r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    assert len(dados) == 1
    assert dados[0]["id"] == "123456"
    assert dados[0]["autor"]["usuario"] == "Usuario Teste"
    assert dados[0]["engajamento"]["curtidas"] == 100


def test_search_all_posts_respeita_delay(monkeypatch):
    sleeps = []

    def fake_sleep(seconds):
        sleeps.append(seconds)

    def fake_search_posts(keyword, pcursor=0, **kwargs):
        return [{"photo_id_str": f"{pcursor}"}]

    monkeypatch.setattr(
        kwai_client.time,
        "sleep",
        fake_sleep,
    )
    monkeypatch.setattr(
        kwai_client,
        "search_posts",
        fake_search_posts,
    )
    resultado = kwai_client.search_all_posts("teste", max_paginas=3, delay=1.5)

    assert len(resultado) == 3
    assert sleeps == [1.5, 1.5]


def test_cli_rejeita_delay_negativo():
    with pytest.raises(SystemExit) as erro:
        main(
            [
                "buscar",
                "futebol",
                "--delay",
                "-1",
            ]
        )
    assert erro.value.code == 2


def test_cli_comentarios_gera_json(
    monkeypatch,
    tmp_path,
):
    arquivo_xml = tmp_path / "window.xml"
    arquivo_xml.write_text("<hierarchy></hierarchy>", encoding="utf-8")

    arquivo_saida = tmp_path / "comentarios.json"

    class FakeProvider:
        def __init__(self, arquivo_xml):
            self.arquivo_xml = arquivo_xml

        def get_comments(self, postagem_url):
            from datetime import UTC, datetime

            from kwai_collector.models.comentario import Comentario

            return [
                Comentario(
                    id=None,
                    postagem_url=postagem_url,
                    autor={
                        "usuario": "usuario_teste",
                        "id": None,
                    },
                    texto="Comentario de teste",
                    curtidas=2,
                    data=None,
                    coletado_em=datetime.now(UTC),
                )
            ]

    monkeypatch.setattr(
        cli,
        "XmlCommentProvider",
        FakeProvider,
    )

    codigo = main(
        [
            "comentarios",
            "https://www.kwai.com/@teste/video/123",
            "--xml",
            str(arquivo_xml),
            "--output",
            str(arquivo_saida),
        ]
    )

    assert codigo == 0
    assert arquivo_saida.exists()

    dados = json.loads(arquivo_saida.read_text(encoding="utf-8"))

    assert len(dados) == 1
    assert dados[0]["texto"] == "Comentario de teste"
    assert dados[0]["curtidas"] == 2

def test_cli_perfil_gera_json(
    monkeypatch,
    tmp_path,
):
    def fake_get_all_profile_posts(
        user_id,
        max_paginas=5,
        delay=0.0,
    ):
        assert user_id == "@teste"
        assert max_paginas == 2
        assert delay == 0.0

        return [
            {
                "photo_id_str": "123456789",
                "kwai_id": "teste",
                "user_name": "Usuario Teste",
                "caption": "Post de teste",
                "time": "2025-09-09 12:00:00",
                "like_count": 10,
                "comment_count": 2,
                "forward_count": 1,
                "view_count": 100,
            }
        ]

    monkeypatch.setattr(
        cli,
        "get_all_profile_posts",
        fake_get_all_profile_posts,
    )

    arquivo_saida = tmp_path / "perfil.json"

    codigo = main(
        [
            "perfil",
            "@teste",
            "--paginas",
            "2",
            "--output",
            str(arquivo_saida),
        ]
    )

    assert codigo == 0
    assert arquivo_saida.exists()

    dados = json.loads(
        arquivo_saida.read_text(encoding="utf-8")
    )

    assert len(dados) == 1
    assert dados[0]["id"] == "123456789"
    assert dados[0]["autor"]["usuario"] == "Usuario Teste"
    assert dados[0]["texto"] == "Post de teste"
def test_cli_comentarios_mobile_json_gera_json(
    monkeypatch,
    tmp_path,
):
    arquivo_mobile = tmp_path / "mobile.json"
    arquivo_mobile.write_text(
        "{}",
        encoding="utf-8",
    )

    arquivo_saida = tmp_path / "comentarios_mobile.json"

    class FakeMobileProvider:
        def __init__(self, arquivo_json):
            self.arquivo_json = arquivo_json

        def get_comments(self, postagem_url):
            from datetime import UTC, datetime

            from kwai_collector.models.comentario import Comentario

            assert self.arquivo_json == arquivo_mobile

            return [
                Comentario(
                    id="123",
                    postagem_url=postagem_url,
                    autor={
                        "usuario": "usuario_mobile",
                        "id": "456",
                    },
                    texto="Comentario mobile",
                    curtidas=10,
                    data=None,
                    coletado_em=datetime.now(UTC),
                )
            ]

    monkeypatch.setattr(
        cli,
        "MobileCommentProvider",
        FakeMobileProvider,
    )

    codigo = main(
        [
            "comentarios",
            "https://www.kwai.com/@teste/video/123",
            "--mobile-json",
            str(arquivo_mobile),
            "--output",
            str(arquivo_saida),
        ]
    )

    assert codigo == 0
    assert arquivo_saida.exists()

    dados = json.loads(
        arquivo_saida.read_text(
            encoding="utf-8",
        )
    )

    assert len(dados) == 1
    assert dados[0]["id"] == "123"
    assert dados[0]["autor"]["usuario"] == "usuario_mobile"
    assert dados[0]["texto"] == "Comentario mobile"
    assert dados[0]["curtidas"] == 10
    assert set(dados[0].keys()) == {"id", "postagem_url", "autor", "texto", "curtidas", "data", "coletado_em"}
    assert set(dados[0]["autor"].keys()) == {"usuario", "id"}
    assert dados[0]["postagem_url"] == "https://www.kwai.com/@teste/video/123"
    assert dados[0]["texto"] == "Comentario mobile"
    assert dados[0]["coletado_em"] is not None