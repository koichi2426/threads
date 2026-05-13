from __future__ import annotations

import os
import random
import time
from typing import Any, Iterator

import requests

from threads_kit.errors import ThreadsAPIError

DEFAULT_BASE = "https://graph.threads.net/v1.0"


def _retry_after_seconds(response: requests.Response) -> float:
    raw = response.headers.get("Retry-After")
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _graph_error_is_ratelimit_or_transient(body: dict[str, Any]) -> bool:
    err = body.get("error")
    if not isinstance(err, dict):
        return False
    code = err.get("code")
    if code in (1, 2, 4, 17, 32, 613, 80004, 80014):
        return True
    sub = err.get("error_subcode")
    if sub in (2446079,):
        return True
    msg = (err.get("message") or "").lower()
    needles = (
        "request limit",
        "rate limit",
        "too many",
        "please reduce",
        "temporarily unavailable",
        "reduce the amount",
        "user request limit",
        "application request limit",
    )
    return any(n in msg for n in needles)


def _http_status_retriable(code: int) -> bool:
    return code == 429 or code in (500, 502, 503, 504)


def _base_url_from_env() -> str:
    v = os.environ.get("THREADS_GRAPH_BASE_URL", "").strip()
    return v if v else DEFAULT_BASE


class ThreadsGraphClient:
    """Threads Graph API への薄い HTTP クライアント。"""

    def __init__(
        self,
        access_token: str,
        *,
        base_url: str | None = None,
        timeout: int = 60,
    ) -> None:
        self.access_token = access_token
        self.base_url = (base_url if base_url is not None else _base_url_from_env()).rstrip("/")
        self.timeout = timeout

    def _get_listing_response(
        self,
        url: str | None,
        path: str,
        initial_params: dict[str, Any],
    ) -> requests.Response:
        if url:
            return requests.get(url, timeout=self.timeout)
        return requests.get(
            f"{self.base_url}/{path.lstrip('/')}",
            params={**initial_params, "access_token": self.access_token},
            timeout=self.timeout,
        )

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """相対パス（先頭の / は任意）に GET し、JSON を dict で返す。"""
        url = f"{self.base_url}/{path.lstrip('/')}"
        q: dict[str, Any] = {"access_token": self.access_token}
        if params:
            q.update(params)
        response = requests.get(url, params=q, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            err = data["error"]
            msg = err.get("message", str(err))
            raise ThreadsAPIError(msg, payload=err)
        return data

    def post_form(self, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """application/x-www-form-urlencoded で POST し、JSON を dict で返す。"""
        url = f"{self.base_url}/{path.lstrip('/')}"
        payload: dict[str, Any] = {}
        for key, value in (data or {}).items():
            if value is None:
                continue
            if isinstance(value, bool):
                payload[key] = str(value).lower()
            else:
                payload[key] = value
        payload["access_token"] = self.access_token
        response = requests.post(url, data=payload, timeout=self.timeout)
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            err = body["error"]
            raise ThreadsAPIError(err.get("message", str(err)), payload=err)
        return body

    def delete_json(self, path: str) -> dict[str, Any]:
        """DELETE（クエリに access_token）。レスポンス JSON を dict で返す。"""
        url = f"{self.base_url}/{path.lstrip('/')}"
        response = requests.delete(
            url,
            params={"access_token": self.access_token},
            timeout=self.timeout,
        )
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            err = body["error"]
            raise ThreadsAPIError(err.get("message", str(err)), payload=err)
        return body

    def iter_paged_items(self, path: str, params: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
        """
        data が配列のページング応答を辿り、各要素を順に yield する。
        paging.next があればフル URL で追従（トークン付き URL をそのまま利用）。
        """
        url: str | None = None
        initial_params = dict(params or {})

        while True:
            response = self._get_listing_response(url, path, initial_params)
            response.raise_for_status()
            body = response.json()
            if "error" in body:
                err = body["error"]
                raise ThreadsAPIError(err.get("message", str(err)), payload=err)

            for item in body.get("data") or []:
                yield item

            url = (body.get("paging") or {}).get("next")
            if not url:
                break

    def iter_paged_items_throttled(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        page_delay_seconds: float = 0.35,
        page_delay_jitter: float = 0.25,
        max_retries_per_page: int = 12,
        backoff_initial: float = 2.0,
        backoff_max: float = 120.0,
    ) -> Iterator[dict[str, Any]]:
        """
        iter_paged_items と同等のページングだが、
        - ページ間にランダムジッタ付きのインターバルを入れる
        - 429 / 5xx / レート制限系の Graph エラーで指数バックオフ＋ Retry-After を尊重して再試行する
        """
        url: str | None = None
        initial_params = dict(params or {})
        first_page = True

        while True:
            if not first_page and page_delay_seconds > 0:
                jitter = random.uniform(0.0, page_delay_jitter) if page_delay_jitter > 0 else 0.0
                time.sleep(page_delay_seconds + jitter)
            first_page = False

            attempt = 0
            body: dict[str, Any] | None = None
            while attempt < max_retries_per_page:
                try:
                    response = self._get_listing_response(url, path, initial_params)
                except requests.RequestException:
                    wait = min(backoff_max, backoff_initial * (2**attempt))
                    time.sleep(wait)
                    attempt += 1
                    if attempt >= max_retries_per_page:
                        raise ThreadsAPIError(
                            "ページ取得のネットワークエラーが続きました。しばらく待ってから再実行してください。"
                        ) from None
                    continue

                if response.status_code == 429 or _http_status_retriable(response.status_code):
                    retry_after = _retry_after_seconds(response) if response.status_code == 429 else 0.0
                    backoff = min(backoff_max, backoff_initial * (2**attempt))
                    time.sleep(max(retry_after, backoff))
                    attempt += 1
                    continue

                if 400 <= response.status_code < 500 and response.status_code != 429:
                    try:
                        parsed_early = response.json()
                    except ValueError:
                        parsed_early = None
                    if (
                        isinstance(parsed_early, dict)
                        and "error" in parsed_early
                        and _graph_error_is_ratelimit_or_transient(parsed_early)
                    ):
                        wait = min(backoff_max, backoff_initial * (2**attempt))
                        time.sleep(wait)
                        attempt += 1
                        continue

                if response.status_code >= 400:
                    response.raise_for_status()

                try:
                    parsed = response.json()
                except ValueError:
                    wait = min(backoff_max, backoff_initial * (2**attempt))
                    time.sleep(wait)
                    attempt += 1
                    continue

                if "error" in parsed:
                    if _graph_error_is_ratelimit_or_transient(parsed):
                        wait = min(backoff_max, backoff_initial * (2**attempt))
                        time.sleep(wait)
                        attempt += 1
                        if attempt >= max_retries_per_page:
                            err = parsed["error"]
                            raise ThreadsAPIError(
                                err.get("message", str(err)),
                                payload=err if isinstance(err, dict) else {},
                            )
                        continue
                    err = parsed["error"]
                    raise ThreadsAPIError(
                        err.get("message", str(err)),
                        payload=err if isinstance(err, dict) else {},
                    )

                body = parsed
                break
            else:
                raise ThreadsAPIError("ページ取得で最大再試行回数に達しました。")

            assert body is not None
            for item in body.get("data") or []:
                yield item

            url = (body.get("paging") or {}).get("next")
            if not url:
                break
