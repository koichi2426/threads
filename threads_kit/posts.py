from __future__ import annotations

from collections.abc import Callable, Iterator

from threads_kit.client import ThreadsGraphClient

DEFAULT_THREAD_FIELDS = "id,text,timestamp,media_url,permalink"


def iter_my_threads(
    client: ThreadsGraphClient,
    *,
    fields: str = DEFAULT_THREAD_FIELDS,
) -> Iterator[dict]:
    """自分のスレッド一覧を 1 件ずつ yield（ページングはクライアント側で処理）。"""
    yield from client.iter_paged_items("me/threads", {"fields": fields})


def fetch_all_my_threads(
    client: ThreadsGraphClient,
    *,
    fields: str = DEFAULT_THREAD_FIELDS,
    on_progress: Callable[[int], None] | None = None,
) -> list[dict]:
    """自分のスレッドを全件リストで返す。"""
    out: list[dict] = []
    for item in iter_my_threads(client, fields=fields):
        out.append(item)
        if on_progress:
            on_progress(len(out))
    return out


def get_thread(client: ThreadsGraphClient, thread_id: str, *, fields: str = DEFAULT_THREAD_FIELDS) -> dict:
    """単一スレッド（メディア ID）を取得する。"""
    return client.get_json(thread_id.lstrip("/"), {"fields": fields})
