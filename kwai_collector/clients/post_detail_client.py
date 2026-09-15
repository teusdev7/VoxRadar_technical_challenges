import json
import re
from html.parser import HTMLParser
from typing import Any

import httpx


class KwaiPostError(RuntimeError):
    """Erro ao obter ou interpretar uma postagem do Kwai."""


class _PageMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()

        self.meta: dict[str, str] = {}
        self.canonical_url: str | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        atributos = dict(attrs)

        if tag == "meta":
            chave = (
                atributos.get("name")
                or atributos.get("property")
            )
            conteudo = atributos.get("content")

            if chave and conteudo:
                self.meta[chave] = conteudo

        elif tag == "link":
            rel = atributos.get("rel")
            href = atributos.get("href")

            if rel == "canonical" and href:
                self.canonical_url = href


def _extrair_script_nuxt(
    html: str,
) -> str:
    """
    Extrai somente o script que contém window.__NUXT__.
    """

    marcador = "window.__NUXT__="

    inicio = html.find(marcador)

    if inicio == -1:
        raise KwaiPostError(
            "window.__NUXT__ não encontrado na página."
        )

    fim = html.find(
        "</script>",
        inicio,
    )

    if fim == -1:
        raise KwaiPostError(
            "Script window.__NUXT__ incompleto."
        )

    return html[inicio:fim]


def _split_js_arguments(
    texto: str,
) -> list[str]:
    """
    Divide os argumentos da função JavaScript sem quebrar
    strings, arrays ou objetos internos.
    """

    argumentos: list[str] = []
    atual: list[str] = []

    profundidade = 0
    aspas: str | None = None
    escape = False

    for caractere in texto:
        if aspas is not None:
            atual.append(caractere)

            if escape:
                escape = False
                continue

            if caractere == "\\":
                escape = True
                continue

            if caractere == aspas:
                aspas = None

            continue

        if caractere in {"'", '"'}:
            aspas = caractere
            atual.append(caractere)
            continue

        if caractere in "([{":
            profundidade += 1
            atual.append(caractere)
            continue

        if caractere in ")]}":
            profundidade -= 1
            atual.append(caractere)
            continue

        if (
            caractere == ","
            and profundidade == 0
        ):
            argumentos.append(
                "".join(atual).strip()
            )

            atual = []
            continue

        atual.append(caractere)

    if atual:
        argumentos.append(
            "".join(atual).strip()
        )

    return argumentos


def _converter_valor_js(
    valor: str,
) -> object:
    """
    Converte valores simples do JavaScript para Python.
    """

    valor = valor.strip()

    if valor == "true":
        return True

    if valor == "false":
        return False

    if valor in {
        "null",
        "undefined",
    }:
        return None

    if (
        valor.startswith('"')
        and valor.endswith('"')
    ):
        try:
            resultado: object = json.loads(
                valor
            )

            return resultado

        except json.JSONDecodeError:
            return valor[1:-1]

    if (
        valor.startswith("'")
        and valor.endswith("'")
    ):
        return valor[1:-1]

    if re.fullmatch(
        r"-?\d+",
        valor,
    ):
        return int(valor)

    if re.fullmatch(
        r"-?\d+\.\d+",
        valor,
    ):
        return float(valor)

    return valor


def _extrair_aliases_nuxt(
    script: str,
) -> dict[str, object]:
    """
    Mapeia aliases da função minificada do Nuxt.

    Exemplo:

    function(a,b,c) {...}(false,0,"texto")

    vira:

    a = False
    b = 0
    c = "texto"
    """

    marcador = "(function("

    inicio_parametros = script.find(
        marcador
    )

    if inicio_parametros == -1:
        raise KwaiPostError(
            "Função interna do __NUXT__ não encontrada."
        )

    inicio_parametros += len(
        marcador
    )

    fim_parametros = script.find(
        "){",
        inicio_parametros,
    )

    if fim_parametros == -1:
        raise KwaiPostError(
            "Parâmetros do __NUXT__ não encontrados."
        )

    parametros_texto = script[
        inicio_parametros:fim_parametros
    ]

    parametros = [
        parametro.strip()
        for parametro in parametros_texto.split(",")
        if parametro.strip()
    ]

    inicio_argumentos = script.rfind(
        "}("
    )

    if inicio_argumentos == -1:
        raise KwaiPostError(
            "Argumentos finais do __NUXT__ "
            "não encontrados."
        )

    argumentos_texto = script[
        inicio_argumentos + 2 :
    ].strip()

    if argumentos_texto.endswith(
        "));"
    ):
        argumentos_texto = (
            argumentos_texto[:-3]
        )

    elif argumentos_texto.endswith(
        ");"
    ):
        argumentos_texto = (
            argumentos_texto[:-2]
        )

    elif argumentos_texto.endswith(
        ")"
    ):
        argumentos_texto = (
            argumentos_texto[:-1]
        )

    argumentos = _split_js_arguments(
        argumentos_texto
    )

    aliases: dict[str, object] = {}

    for parametro, argumento in zip(
        parametros,
        argumentos,
        strict=False,
    ):
        aliases[parametro] = (
            _converter_valor_js(
                argumento
            )
        )

    return aliases


def _resolver_token(
    token: str,
    aliases: dict[str, object],
) -> object:
    token = token.strip()

    if token in aliases:
        return aliases[token]

    return _converter_valor_js(
        token
    )


def _extrair_objeto_principal(
    script: str,
    expected_photo_id: str | None = None,
) -> str:
    """
    Localiza o objeto JavaScript correspondente ao post.

    Não depende de nomes temporários como O[0].
    """

    if expected_photo_id is not None:
        padrao = re.compile(
            r'photo_id_str\s*:\s*"'
            + re.escape(
                expected_photo_id
            )
            + r'"'
        )

    else:
        padrao = re.compile(
            r'photo_id_str\s*:\s*"[^"]+"'
        )

    resultado = padrao.search(
        script
    )

    if resultado is None:
        raise KwaiPostError(
            "photo_id_str da postagem "
            "não encontrado no __NUXT__."
        )

    posicao_photo_id = (
        resultado.start()
    )

    pilha_chaves: list[int] = []

    aspas: str | None = None
    escape = False

    for indice in range(
        posicao_photo_id + 1
    ):
        caractere = script[indice]

        if aspas is not None:
            if escape:
                escape = False
                continue

            if caractere == "\\":
                escape = True
                continue

            if caractere == aspas:
                aspas = None

            continue

        if caractere in {
            "'",
            '"',
        }:
            aspas = caractere
            continue

        if caractere == "{":
            pilha_chaves.append(
                indice
            )

        elif (
            caractere == "}"
            and pilha_chaves
        ):
            pilha_chaves.pop()

    if not pilha_chaves:
        raise KwaiPostError(
            "Não foi possível encontrar "
            "o início do objeto da postagem."
        )

    inicio_objeto = (
        pilha_chaves[-1]
    )

    profundidade = 0
    aspas = None
    escape = False

    for indice in range(
        inicio_objeto,
        len(script),
    ):
        caractere = script[indice]

        if aspas is not None:
            if escape:
                escape = False
                continue

            if caractere == "\\":
                escape = True
                continue

            if caractere == aspas:
                aspas = None

            continue

        if caractere in {
            "'",
            '"',
        }:
            aspas = caractere
            continue

        if caractere == "{":
            profundidade += 1

        elif caractere == "}":
            profundidade -= 1

            if profundidade == 0:
                return script[
                    inicio_objeto :
                    indice + 1
                ]

    raise KwaiPostError(
        "Não foi possível encontrar "
        "o final do objeto da postagem."
    )


def _extrair_campo_objeto(
    objeto: str,
    campo: str,
    aliases: dict[str, object],
) -> object:
    """
    Extrai campos como:

    caption:k
    like_count:W
    user_name:y
    photo_id_str:"123"
    """

    padrao = re.compile(
        rf"\b{re.escape(campo)}\s*:\s*"
        r'("(?:\\.|[^"])*"'
        r"|'(?:\\.|[^'])*'"
        r"|[A-Za-z_$][A-Za-z0-9_$]*"
        r"|-?\d+(?:\.\d+)?)"
    )

    resultado = padrao.search(
        objeto
    )

    if resultado is None:
        return None

    return _resolver_token(
        resultado.group(1),
        aliases,
    )


def _extrair_numero_seo(
    descricao: str | None,
    nome: str,
) -> int | None:
    """
    Extrai valores de textos como:

    10942 Like(s), 69 Comment(s)
    """

    if not descricao:
        return None

    padrao = re.compile(
        rf"([\d.,]+)\s+"
        rf"{re.escape(nome)}\(s\)",
        re.IGNORECASE,
    )

    resultado = padrao.search(
        descricao
    )

    if resultado is None:
        return None

    numero = re.sub(
        r"[^\d]",
        "",
        resultado.group(1),
    )

    if not numero:
        return None

    return int(numero)


def _extrair_data_estruturada(
    script: str,
    campo: str,
) -> str | None:
    """
    Extrai campos estruturados como:

    uploadDate:"..."
    duration:"..."
    """

    padrao = re.compile(
        rf'{re.escape(campo)}\s*:\s*"([^"]+)"'
    )

    resultado = padrao.search(
        script
    )

    if resultado is None:
        return None

    return resultado.group(1)


def get_post_details(
    url: str,
    expected_photo_id: str | None = None,
) -> dict[str, Any]:
    """
    Busca a página pública de uma postagem do Kwai
    e extrai seus principais dados.
    """

    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/120.0.0.0 "
                    "Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,"
                    "image/avif,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": (
                    "pt-BR,pt;q=0.9,"
                    "en-US;q=0.8,en;q=0.7"
                ),
            },
            timeout=30.0,
        )

        response.raise_for_status()

    except httpx.HTTPStatusError as exc:
        raise KwaiPostError(
            "Falha ao obter a página da postagem: "
            f"HTTP {exc.response.status_code}"
        ) from exc

    except httpx.RequestError as exc:
        raise KwaiPostError(
            "Falha de conexão ao obter "
            f"a postagem: {exc}"
        ) from exc

    html = response.text

    if not html:
        raise KwaiPostError(
            "A página da postagem retornou "
            "um HTML vazio."
        )

    metadata_parser = (
        _PageMetadataParser()
    )

    metadata_parser.feed(
        html
    )

    script_nuxt = (
        _extrair_script_nuxt(
            html
        )
    )

    aliases = (
        _extrair_aliases_nuxt(
            script_nuxt
        )
    )

    objeto = (
        _extrair_objeto_principal(
            script_nuxt,
            expected_photo_id=(
                expected_photo_id
            ),
        )
    )

    photo_id = (
        _extrair_campo_objeto(
            objeto,
            "photo_id_str",
            aliases,
        )
    )

    if photo_id is None:
        raise KwaiPostError(
            "photo_id_str não encontrado."
        )

    photo_id_str = str(
        photo_id
    )

    if (
        expected_photo_id is not None
        and photo_id_str
        != expected_photo_id
    ):
        raise KwaiPostError(
            "O photo_id retornado pela página "
            "não corresponde ao solicitado."
        )

    user_name = (
        _extrair_campo_objeto(
            objeto,
            "user_name",
            aliases,
        )
    )

    user_id = (
        _extrair_campo_objeto(
            objeto,
            "user_id_str",
            aliases,
        )
    )

    kwai_id = (
        _extrair_campo_objeto(
            objeto,
            "kwai_id",
            aliases,
        )
    )

    caption = (
        _extrair_campo_objeto(
            objeto,
            "caption",
            aliases,
        )
    )

    time_value = (
        _extrair_campo_objeto(
            objeto,
            "time",
            aliases,
        )
    )

    timestamp = (
        _extrair_campo_objeto(
            objeto,
            "timestamp",
            aliases,
        )
    )

    curtidas = (
        _extrair_campo_objeto(
            objeto,
            "like_count",
            aliases,
        )
    )

    comentarios = (
        _extrair_campo_objeto(
            objeto,
            "comment_count",
            aliases,
        )
    )

    compartilhamentos = (
        _extrair_campo_objeto(
            objeto,
            "forward_count",
            aliases,
        )
    )

    visualizacoes = (
        _extrair_campo_objeto(
            objeto,
            "view_count",
            aliases,
        )
    )

    seo_description = (
        metadata_parser.meta.get(
            "description"
        )
    )

    comentarios_seo = (
        _extrair_numero_seo(
            seo_description,
            "Comment",
        )
    )

    curtidas_seo = (
        _extrair_numero_seo(
            seo_description,
            "Like",
        )
    )

    canonical_url = (
        metadata_parser.canonical_url
        or str(response.url)
    )

    thumbnail = (
        metadata_parser.meta.get(
            "og:image"
        )
    )

    descricao = (
        metadata_parser.meta.get(
            "og:description"
        )
    )

    upload_date = (
        _extrair_data_estruturada(
            script_nuxt,
            "uploadDate",
        )
    )

    duracao = (
        _extrair_data_estruturada(
            script_nuxt,
            "duration",
        )
    )

    url_perfil: str | None = None

    if kwai_id is not None:
        url_perfil = (
            "https://www.kwai.com/@"
            f"{kwai_id}"
        )

    return {
        "photo_id": photo_id_str,
        "url": canonical_url,
        "autor": {
            "nome": user_name,
            "usuario": kwai_id,
            "id": user_id,
            "url_perfil": url_perfil,
        },
        "caption": caption,
        "descricao": descricao,
        "publicado_em": upload_date,
        "data_original": time_value,
        "timestamp": timestamp,
        "duracao": duracao,
        "thumbnail": thumbnail,
        "engajamento": {
            "curtidas": curtidas,
            "comentarios": comentarios,
            "compartilhamentos": (
                compartilhamentos
            ),
            "visualizacoes": visualizacoes,
            "curtidas_seo": curtidas_seo,
            "comentarios_seo": (
                comentarios_seo
            ),
        },
    }