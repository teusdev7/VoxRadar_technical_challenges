from time import time

from kwai_collector.clients.comment_client import (
    KwaiCommentsError,
    get_tiny_comments,
)

# Coloque aqui o photo_id real do vídeo.
PHOTO_ID = "5253599077813406650"


def main() -> None:
    timestamp = str(int(time() * 1000))

    query_params = {
        # ----------------------------------------------------
        # VALORES CONFIRMADOS NO APK
        # ----------------------------------------------------
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

        # ----------------------------------------------------
        # VALORES REAIS DO SEU APARELHO
        # ----------------------------------------------------
        "sys": "KWAI_ANDROID_14",
        "mod": "samsung(SM-A356E)",
        "net": "WIFI",
        "language": "pt-br",
        "country_code": "br",
        "mcc": "724",

        # O APK usa:
        # displayName + " " + timezone ID
        #
        # O ID real do aparelho é:
        # America/Sao_Paulo
        #
        # Ainda não confirmamos o displayName exato
        # retornado pelo Java no aparelho.
        "time_zone": (
            "Brasilia Standard Time "
            "America/Sao_Paulo"
        ),

        # ----------------------------------------------------
        # VALORES AINDA NÃO CONFIRMADOS EM RUNTIME
        # ----------------------------------------------------

        # Device classifier.
        # -1 é o valor inicial/fallback observado no APK.
        "ds": "-1",

        # egid aparece como vazio no código Java visível.
        "egid": "",

        # ABI real do aparelho.
        "abi": "arm64-v8a",

        # System.currentTimeMillis()
        "timestamp": timestamp,
    }

    print()
    print("=" * 60)
    print("TESTE TINY API")
    print("=" * 60)
    print("PHOTO_ID:", PHOTO_ID)
    print("TIMESTAMP:", timestamp)
    print()

    try:
        comments = get_tiny_comments(
            photo_id=PHOTO_ID,
            query_params=query_params,
            debug=True,
        )

        print()
        print("=" * 60)
        print("RESULTADO")
        print("=" * 60)

        print(
            "Quantidade de comentários:",
            len(comments),
        )

        if not comments:
            print()
            print(
                "A API retornou uma lista vazia "
                "de comentários."
            )

        for index, comment in enumerate(
            comments[:10],
            start=1,
        ):
            print()
            print("-" * 60)

            print(
                f"COMENTÁRIO {index}"
            )

            print(
                "ID:",
                comment.get("commentId"),
            )

            print(
                "USUÁRIO:",
                comment.get("userName"),
            )

            print(
                "USER ID:",
                comment.get("userId"),
            )

            print(
                "CONTEÚDO:",
                comment.get("content"),
            )

            print(
                "CURTIDAS:",
                comment.get("commentLikeCount"),
            )

            print(
                "DATA:",
                comment.get("commentTime"),
            )

            print(
                "SUBCOMENTÁRIOS:",
                comment.get("sub_comment_count"),
            )

    except KwaiCommentsError as exc:
        print()
        print("=" * 60)
        print("ERRO DA API")
        print("=" * 60)

        print(exc)

    except KeyboardInterrupt:
        print()
        print("Teste interrompido.")


if __name__ == "__main__":
    main()