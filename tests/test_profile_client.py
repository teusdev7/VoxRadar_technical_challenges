import httpx

from kwai_collector.clients import profile_client


class FakeResonse:
    status_code = 200
    
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "result": 1,
            "cursor": "cursor_proxima_pagina",
            "feeds": [
                {
                    "photo_id_str": "1234567890",
                    "user_name": "Mateus Fonseca",
                },
                {
                    "photo_id_str": "0987654321",
                    "user_name": "Lucas Soares",
                },
            ],
        }


def test_get_profile_page(monkeypatch):
    def fake_post(url, json, headers):
        assert url == "https://www.kwai.com/rest/o/w/pc/feed/profile"
        assert json["userId"] == "@LucasSoares"
        assert json["pcursor"] == ""
        assert json["count"] == 20

        return FakeResonse()

    monkeypatch.setattr(httpx, "post", fake_post)
    feeds, cursor = profile_client.get_profile_page(user_id="@LucasSoares", pcursor="")
    assert len(feeds) == 2
    assert feeds[0]["photo_id_str"] == "1234567890"
    assert cursor == "cursor_proxima_pagina"

def test_get_profile_page_faz_retry_em_429(monkeypatch):
    chamadas = 0
    esperas = []

    class FakeResponse:
        def __init__(self, status_code):
            self.status_code = status_code

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "feeds": [
                    {
                        "photo_id_str": "123",
                    }
                ],
                "cursor": None,
            }

    def fake_post(url, json, headers):
        nonlocal chamadas

        chamadas += 1

        if chamadas == 1:
            return FakeResponse(429)

        return FakeResponse(200)

    def fake_sleep(segundos):
        esperas.append(segundos)

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(
        profile_client.time,
        "sleep",
        fake_sleep,
    )

    feeds, cursor = profile_client.get_profile_page(
        user_id="@teste",
        max_tentativas=3,
        backoff_base=1.0,
    )

    assert chamadas == 2
    assert esperas == [1.0]
    assert len(feeds) == 1
    assert cursor is None

def test_get_all_profile_posts_respeita_delay(monkeypatch):
    esperas = []

    def fake_get_profile_page(
        user_id,
        pcursor="",
    ):
        assert user_id == "@teste"

        if pcursor == "":
            return [
                {"photo_id_str": "111"},
            ], "cursor_2"

        return [
            {"photo_id_str": "222"},
        ], None

    def fake_sleep(segundos):
        esperas.append(segundos)

    monkeypatch.setattr(
        profile_client,
        "get_profile_page",
        fake_get_profile_page,
    )

    monkeypatch.setattr(
        profile_client.time,
        "sleep",
        fake_sleep,
    )

    posts = profile_client.get_all_profile_posts(
        user_id="@teste",
        max_paginas=2,
        delay=0.5,
    )

    assert len(posts) == 2
    assert esperas == [0.5]
