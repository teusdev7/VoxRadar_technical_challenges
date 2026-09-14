from typing import Any

A1_Radar = "A1_Radar"

ROOT_COMMENTS_ENDPOINT = "/rest/o/comment/list/v2"
SUB_COMMENTS_ENDPOINT = "/rest/o/comment/sublist"

END_CURSORS = {
    "",
    "no_more",
    "more_cursor_total",
}


def is_end_cursor(cursor: str | None) -> bool:
    return cursor is None or cursor in END_CURSORS


def get_root_comments(
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    comments = data.get("rootComments")

    if not isinstance(comments, list):
        return []

    return [
        item
        for item in comments
        if isinstance(item, dict)
    ]


def get_subcomments(
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    comments = data.get("subComments")

    if not isinstance(comments, list):
        return []

    return [
        item
        for item in comments
        if isinstance(item, dict)
    ]


def get_pcursor(
    data: dict[str, Any],
) -> str | None:
    cursor = data.get("pcursor")

    if cursor is None:
        return None

    return str(cursor)


def build_root_payload(
    photo_id: str,
    user_id: str,
    pcursor: str = "",
    count: int = 10,
) -> dict[str, str]:
    return {
        "photoId": str(photo_id),
        "user_id": str(user_id),
        "order": "desc",
        "pcursor": pcursor,
        "count": str(count),
        "photoPageType": "0",
        "requestType": "3",
        "isPreload": "false",
        "preloadSource": "",
        "os": "android",
    }


def build_subcomment_payload(
    photo_id: str,
    user_id: str,
    root_comment_id: str,
    pcursor: str = "",
    count: int = 3,
    repeat_comment_ids: list[str] | None = None,
) -> dict[str, str]:
    repeat_ids = ",".join(
        repeat_comment_ids or []
    )

    return {
        "photoId": str(photo_id),
        "user_id": str(user_id),
        "order": "desc",
        "pcursor": pcursor,
        "rootCommentId": str(root_comment_id),
        "count": str(count),
        "repeatCommentIds": repeat_ids,
    }

def get_comment_id(
    comment: dict[str, Any],
) -> str | None:
    comment_id = comment.get("comment_id")

    if comment_id is None:
        comment_id = comment.get("commentId")

    if comment_id is None:
        return None

    return str(comment_id)


def collect_root_pages(
    pages: list[dict[str, Any]],
    max_comments: int | None = None,
) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    previous_cursor: str | None = None

    for data in pages:
        comments = get_root_comments(data)

        new_items = 0

        for comment in comments:
            comment_id = get_comment_id(comment)

            identifier = (
                comment_id
                if comment_id is not None
                else repr(comment)
            )

            if identifier in seen_ids:
                continue

            seen_ids.add(identifier)
            collected.append(comment)
            new_items += 1

            if (
                max_comments is not None
                and len(collected) >= max_comments
            ):
                return collected[:max_comments]

        cursor = get_pcursor(data)

        if is_end_cursor(cursor):
            break

        if cursor == previous_cursor:
            break

        if not comments and new_items == 0:
            break

        previous_cursor = cursor

    return collected


def collect_subcomment_pages(
    pages: list[dict[str, Any]],
    embedded: list[dict[str, Any]] | None = None,
    max_subcomments: int | None = None,
) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for comment in embedded or []:
        comment_id = get_comment_id(comment)

        identifier = (
            comment_id
            if comment_id is not None
            else repr(comment)
        )

        if identifier in seen_ids:
            continue

        seen_ids.add(identifier)
        collected.append(comment)

        if (
            max_subcomments is not None
            and len(collected) >= max_subcomments
        ):
            return collected[:max_subcomments]

    previous_cursor: str | None = None

    for data in pages:
        comments = get_subcomments(data)
        new_items = 0

        for comment in comments:
            comment_id = get_comment_id(comment)

            identifier = (
                comment_id
                if comment_id is not None
                else repr(comment)
            )

            if identifier in seen_ids:
                continue

            seen_ids.add(identifier)
            collected.append(comment)
            new_items += 1

            if (
                max_subcomments is not None
                and len(collected) >= max_subcomments
            ):
                return collected[:max_subcomments]

        cursor = get_pcursor(data)

        if is_end_cursor(cursor):
            break

        if cursor == previous_cursor:
            break

        if not comments and new_items == 0:
            break

        previous_cursor = cursor

    return collected