from __future__ import annotations

import json
import sys
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


def iter_user_threads(
    client: ThreadsGraphClient,
    *,
    user_path: str = "me",
    fields: str = DEFAULT_THREAD_FIELDS,
    page_delay_seconds: float = 0.35,
    page_delay_jitter: float = 0.25,
    max_retries_per_page: int = 12,
    backoff_initial: float = 2.0,
    backoff_max: float = 120.0,
) -> Iterator[dict]:
    """
    指定ユーザー（既定は me）のスレッドを全ページ走査する。
    ページ間インターバル・再試行は iter_paged_items_throttled に委譲。
    """
    up = user_path.strip().rstrip("/") or "me"
    yield from client.iter_paged_items_throttled(
        f"{up}/threads",
        {"fields": fields},
        page_delay_seconds=page_delay_seconds,
        page_delay_jitter=page_delay_jitter,
        max_retries_per_page=max_retries_per_page,
        backoff_initial=backoff_initial,
        backoff_max=backoff_max,
    )


def export_threads_json_array_stream(
    out_path: str,
    iterator: Iterator[dict],
    *,
    pretty: bool = False,
    quiet: bool = False,
    progress_every: int = 25,
) -> int:
    """
    スレッド一覧を JSON 配列で出力する。
    - ファイルかつ非 pretty: 1 件ずつ書き込み（配列全体をメモリに載せない）
    - stdout または pretty: メモリに蓄積してから出力（件数が多いときは注意）
    """
    count = 0
    use_stdout = out_path == "-"

    def maybe_progress(n: int) -> None:
        if quiet or not progress_every or n % progress_every != 0:
            return
        print(f"... {n} 件取得", file=sys.stderr)

    if use_stdout or pretty:
        items: list[dict] = []
        for item in iterator:
            items.append(item)
            count += 1
            maybe_progress(count)
        text = json_dumps_array(items, pretty=pretty)
        if use_stdout:
            sys.stdout.write(text)
            if not text.endswith("\n"):
                sys.stdout.write("\n")
        else:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
        return count

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("[")
        first = True
        for item in iterator:
            maybe_progress(count + 1)
            if not first:
                f.write(",")
            first = False
            f.write(_json_dumps_one(item, compact=True))
            count += 1
        f.write("]")
    return count


def json_dumps_array(items: list[dict], *, pretty: bool) -> str:
    if pretty:
        return json.dumps(items, ensure_ascii=False, indent=2) + "\n"
    return json.dumps(items, ensure_ascii=False, separators=(",", ":")) + "\n"


def _json_dumps_one(item: dict, *, compact: bool) -> str:
    if compact:
        return json.dumps(item, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(item, ensure_ascii=False, indent=2)


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
