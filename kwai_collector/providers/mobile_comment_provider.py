import json
from pathlib import Path
from typing import Any

from kwai_collector.clients.mobile_comment_client import (
    collect_root_pages,
)
from kwai_collector.models.comentario import Comentario
from kwai_collector.parsers.comment_parser import parse_comment


class MobileCommentProvider:
    def __init__(
        self,
        arquivo_json: Path,
    ) -> None:
        self.arquivo_json = arquivo_json

    def _load_pages(
        self,
    ) -> list[dict[str, Any]]:
        with self.arquivo_json.open(
            "r",
            encoding="utf-8",
        ) as arquivo:
            data: Any = json.load(arquivo)

        if isinstance(data, dict):
            pages_raw = data.get("pages")

            if isinstance(pages_raw, list):
                return [
                    page
                    for page in pages_raw
                    if isinstance(page, dict)
                ]

            return [data]

        if isinstance(data, list):
            return [
                page
                for page in data
                if isinstance(page, dict)
            ]

        raise ValueError(
            "O arquivo mobile deve conter "
            "um objeto JSON ou uma lista de páginas."
        )

    def get_comments(
        self,
        postagem_url: str,
    ) -> list[Comentario]:
        pages = self._load_pages()

        comentarios_brutos = collect_root_pages(
            pages
        )

        return [
            parse_comment(
                comentario,
                postagem_url,
            )
            for comentario in comentarios_brutos
        ]