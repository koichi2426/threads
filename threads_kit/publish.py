from __future__ import annotations

import time
from typing import Any

from threads_kit.client import ThreadsGraphClient


def create_threads_container(
    client: ThreadsGraphClient,
    *,
    user_path: str = "me",
    media_type: str,
    text: str | None = None,
    image_url: str | None = None,
    video_url: str | None = None,
    reply_to_id: str | None = None,
    reply_control: str | None = None,
    link_attachment: str | None = None,
    topic_tag: str | None = None,
    is_carousel_item: bool | None = None,
    children: str | None = None,
    auto_publish_text: bool = False,
    alt_text: str | None = None,
    quote_post_id: str | None = None,
) -> dict[str, Any]:
    """
    POST /{threads-user-id}/threads — メディアコンテナを作成する。
    media_type は TEXT / IMAGE / VIDEO / CAROUSEL（用途に応じ公式参照）。
    """
    data: dict[str, Any] = {"media_type": media_type}
    if text is not None:
        data["text"] = text
    if image_url is not None:
        data["image_url"] = image_url
    if video_url is not None:
        data["video_url"] = video_url
    if reply_to_id is not None:
        data["reply_to_id"] = reply_to_id
    if reply_control is not None:
        data["reply_control"] = reply_control
    if link_attachment is not None:
        data["link_attachment"] = link_attachment
    if topic_tag is not None:
        data["topic_tag"] = topic_tag
    if is_carousel_item is not None:
        data["is_carousel_item"] = is_carousel_item
    if children is not None:
        data["children"] = children
    if auto_publish_text:
        data["auto_publish_text"] = True
    if alt_text is not None:
        data["alt_text"] = alt_text
    if quote_post_id is not None:
        data["quote_post_id"] = quote_post_id
    return client.post_form(f"{user_path.rstrip('/')}/threads", data)


def publish_container(
    client: ThreadsGraphClient,
    creation_id: str,
    *,
    user_path: str = "me",
) -> dict[str, Any]:
    """POST /{threads-user-id}/threads_publish — creation_id のコンテナを公開する。"""
    return client.post_form(
        f"{user_path.rstrip('/')}/threads_publish",
        {"creation_id": creation_id},
    )


def get_container_status(
    client: ThreadsGraphClient,
    container_id: str,
    *,
    fields: str = "id,status,error_message",
) -> dict[str, Any]:
    """GET /{container-id}?fields=... — コンテナの処理状態を確認する。"""
    return client.get_json(container_id.lstrip("/"), {"fields": fields})


def publish_text_post(
    client: ThreadsGraphClient,
    text: str,
    *,
    user_path: str = "me",
    auto_publish: bool = False,
    wait_seconds: float = 0,
    reply_to_id: str | None = None,
    reply_control: str | None = None,
    link_attachment: str | None = None,
    topic_tag: str | None = None,
) -> dict[str, Any]:
    """
    テキスト投稿。auto_publish=True のときは auto_publish_text で 1 リクエストで公開まで行う。
    False のときはコンテナ作成後に wait_seconds 待ち、threads_publish する。
    """
    if auto_publish:
        return create_threads_container(
            client,
            user_path=user_path,
            media_type="TEXT",
            text=text,
            reply_to_id=reply_to_id,
            reply_control=reply_control,
            link_attachment=link_attachment,
            topic_tag=topic_tag,
            auto_publish_text=True,
        )
    created = create_threads_container(
        client,
        user_path=user_path,
        media_type="TEXT",
        text=text,
        reply_to_id=reply_to_id,
        reply_control=reply_control,
        link_attachment=link_attachment,
        topic_tag=topic_tag,
    )
    cid = created.get("id")
    if not cid:
        return created
    if wait_seconds > 0:
        time.sleep(wait_seconds)
    return publish_container(client, str(cid), user_path=user_path)


def publish_image_post(
    client: ThreadsGraphClient,
    *,
    image_url: str,
    text: str | None = None,
    user_path: str = "me",
    wait_seconds: float = 5.0,
    alt_text: str | None = None,
) -> dict[str, Any]:
    """画像 URL（公開 URL）でコンテナ作成 → 待機 → 公開。"""
    created = create_threads_container(
        client,
        user_path=user_path,
        media_type="IMAGE",
        image_url=image_url,
        text=text,
        alt_text=alt_text,
    )
    cid = created.get("id")
    if not cid:
        return created
    if wait_seconds > 0:
        time.sleep(wait_seconds)
    return publish_container(client, str(cid), user_path=user_path)


def publish_video_post(
    client: ThreadsGraphClient,
    *,
    video_url: str,
    text: str | None = None,
    user_path: str = "me",
    wait_seconds: float = 10.0,
    alt_text: str | None = None,
) -> dict[str, Any]:
    """動画 URL（公開 URL）でコンテナ作成 → 待機 → 公開。"""
    created = create_threads_container(
        client,
        user_path=user_path,
        media_type="VIDEO",
        video_url=video_url,
        text=text,
        alt_text=alt_text,
    )
    cid = created.get("id")
    if not cid:
        return created
    if wait_seconds > 0:
        time.sleep(wait_seconds)
    return publish_container(client, str(cid), user_path=user_path)


def repost(client: ThreadsGraphClient, media_id: str) -> dict[str, Any]:
    """POST /{threads-media-id}/repost"""
    mid = media_id.lstrip("/")
    return client.post_form(f"{mid}/repost", {})


def delete_media(client: ThreadsGraphClient, media_id: str) -> dict[str, Any]:
    """DELETE /{threads-media-id}"""
    return client.delete_json(media_id.lstrip("/"))
