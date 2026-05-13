from __future__ import annotations

from threads_kit.client import ThreadsGraphClient

DEFAULT_ME_FIELDS = "id,username,name,threads_profile_picture_url,threads_biography"


def get_me(client: ThreadsGraphClient, fields: str = DEFAULT_ME_FIELDS) -> dict:
    """ログイン中ユーザー（/me）のプロフィールを取得する。"""
    return client.get_json("me", {"fields": fields})
