import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse


def numero_nao_negativo(
    value: str,
) -> float:
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
    valor: str,
) -> str:
    nome = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        valor,
    )

    return nome.strip(
        "._-"
    ) or "resultado"


def extrair_photo_id(
    valor: str,
) -> str:
    valor = valor.strip()

    if valor.isdigit():
        return valor

    parsed = urlparse(
        valor
    )

    partes = [
        parte
        for parte in parsed.path.split("/")
        if parte
    ]

    ids_numericos = [
        parte
        for parte in partes
        if parte.isdigit()
    ]

    if ids_numericos:
        return ids_numericos[-1]

    raise ValueError(
        "Não foi possível identificar o photo_id "
        "na URL informada."
    )