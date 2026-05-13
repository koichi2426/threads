from __future__ import annotations

import os
from typing import Any, Iterator

import requests

from threads_kit.errors import ThreadsAPIError

DEFAULT_BASE = "https://graph.threads.net/v1.0"


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
            if url:
                response = requests.get(url, timeout=self.timeout)
            else:
                response = requests.get(
                    f"{self.base_url}/{path.lstrip('/')}",
                    params={**initial_params, "access_token": self.access_token},
                    timeout=self.timeout,
                )
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
