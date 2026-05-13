from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from threads_kit.client import ThreadsGraphClient
from threads_kit.errors import ThreadsAPIError
from threads_kit import posts, profile, publish


def _try_load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def _resolve_token(explicit: str | None) -> str:
    if explicit:
        return explicit
    token = os.environ.get("THREADS_ACCESS_TOKEN", "").strip()
    if not token or token == "YOUR_GENERATED_TOKEN":
        print(
            "エラー: トークンがありません。環境変数 THREADS_ACCESS_TOKEN を設定するか、"
            "--token を指定してください。",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


def _client(args: argparse.Namespace) -> ThreadsGraphClient:
    return ThreadsGraphClient(_resolve_token(args.token))


def cmd_me(args: argparse.Namespace) -> None:
    client = _client(args)
    data = profile.get_me(client, fields=args.fields)
    print(json.dumps(data, ensure_ascii=False, indent=2 if args.pretty else None))


def cmd_threads_list(args: argparse.Namespace) -> None:
    client = _client(args)
    n = 0
    for item in posts.iter_my_threads(client, fields=args.fields):
        n += 1
        line = json.dumps(item, ensure_ascii=False)
        print(line)
        if args.limit and n >= args.limit:
            break


def cmd_threads_backup(args: argparse.Namespace) -> None:
    client = _client(args)

    def on_progress(count: int) -> None:
        if args.quiet:
            return
        print(f"現在 {count} 件取得済み...")

    try:
        items = posts.fetch_all_my_threads(
            client,
            fields=args.fields,
            on_progress=on_progress,
        )
    except ThreadsAPIError as e:
        print(f"API エラー: {e}", file=sys.stderr)
        sys.exit(1)

    if not items:
        print("投稿データが見つかりませんでした。")
        return

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2 if args.pretty else None)

    if not args.quiet:
        print(f"\n完了！合計 {len(items)} 件を '{args.output}' に保存しました。")


def cmd_threads_export_all(args: argparse.Namespace) -> None:
    """全ページをスロットリング付きで取得し JSON 配列として書き出す。"""
    client = _client(args)
    iterator = posts.iter_user_threads(
        client,
        user_path=args.user_path,
        fields=args.fields,
        page_delay_seconds=args.page_delay,
        page_delay_jitter=args.page_jitter,
        max_retries_per_page=args.max_retries,
        backoff_initial=args.backoff_initial,
        backoff_max=args.backoff_max,
    )
    try:
        n = posts.export_threads_json_array_stream(
            args.output,
            iterator,
            pretty=args.pretty,
            quiet=args.quiet,
            progress_every=args.progress_every,
        )
    except ThreadsAPIError as e:
        print(f"API エラー: {e}", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        if args.output == "-":
            print(f"\n完了。合計 {n} 件を標準出力に書き出しました。", file=sys.stderr)
        else:
            print(f"\n完了。合計 {n} 件を '{args.output}' に書き出しました。", file=sys.stderr)


def cmd_thread_get(args: argparse.Namespace) -> None:
    client = _client(args)
    data = posts.get_thread(client, args.thread_id, fields=args.fields)
    print(json.dumps(data, ensure_ascii=False, indent=2 if args.pretty else None))


def _print_json(data: object, pretty: bool) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2 if pretty else None))


def _load_post_body(args: argparse.Namespace) -> str:
    if args.stdin:
        body = sys.stdin.read()
    elif args.file is not None:
        body = Path(args.file).read_text(encoding="utf-8")
    else:
        body = args.text or ""
    return body.strip()


def cmd_post_text(args: argparse.Namespace) -> None:
    text = _load_post_body(args)
    if not text:
        print("エラー: 投稿本文が空です。", file=sys.stderr)
        sys.exit(1)
    client = _client(args)
    try:
        data = publish.publish_text_post(
            client,
            text,
            user_path=args.user_path,
            auto_publish=args.auto_publish,
            wait_seconds=args.wait,
            reply_to_id=args.reply_to,
            reply_control=args.reply_control,
            link_attachment=args.link_attachment,
            topic_tag=args.topic_tag,
        )
    except ThreadsAPIError as e:
        print(f"API エラー: {e}", file=sys.stderr)
        sys.exit(1)
    _print_json(data, args.pretty)


def cmd_post_image(args: argparse.Namespace) -> None:
    client = _client(args)
    try:
        data = publish.publish_image_post(
            client,
            image_url=args.image_url,
            text=args.text,
            user_path=args.user_path,
            wait_seconds=args.wait,
            alt_text=args.alt_text,
        )
    except ThreadsAPIError as e:
        print(f"API エラー: {e}", file=sys.stderr)
        sys.exit(1)
    _print_json(data, args.pretty)


def cmd_post_video(args: argparse.Namespace) -> None:
    client = _client(args)
    try:
        data = publish.publish_video_post(
            client,
            video_url=args.video_url,
            text=args.text,
            user_path=args.user_path,
            wait_seconds=args.wait,
            alt_text=args.alt_text,
        )
    except ThreadsAPIError as e:
        print(f"API エラー: {e}", file=sys.stderr)
        sys.exit(1)
    _print_json(data, args.pretty)


def cmd_publish(args: argparse.Namespace) -> None:
    client = _client(args)
    if args.wait > 0:
        time.sleep(args.wait)
    try:
        data = publish.publish_container(client, args.creation_id, user_path=args.user_path)
    except ThreadsAPIError as e:
        print(f"API エラー: {e}", file=sys.stderr)
        sys.exit(1)
    _print_json(data, args.pretty)


def cmd_container_create(args: argparse.Namespace) -> None:
    client = _client(args)
    try:
        data = publish.create_threads_container(
            client,
            user_path=args.user_path,
            media_type=args.media_type,
            text=args.text,
            image_url=args.image_url,
            video_url=args.video_url,
            reply_to_id=args.reply_to,
            reply_control=args.reply_control,
            link_attachment=args.link_attachment,
            topic_tag=args.topic_tag,
            is_carousel_item=args.is_carousel_item,
            children=args.children,
            auto_publish_text=args.auto_publish_text,
            alt_text=args.alt_text,
            quote_post_id=args.quote_post_id,
        )
    except ThreadsAPIError as e:
        print(f"API エラー: {e}", file=sys.stderr)
        sys.exit(1)
    _print_json(data, args.pretty)


def cmd_container_status(args: argparse.Namespace) -> None:
    client = _client(args)
    try:
        data = publish.get_container_status(client, args.container_id, fields=args.fields)
    except ThreadsAPIError as e:
        print(f"API エラー: {e}", file=sys.stderr)
        sys.exit(1)
    _print_json(data, args.pretty)


def cmd_delete(args: argparse.Namespace) -> None:
    client = _client(args)
    try:
        data = publish.delete_media(client, args.media_id)
    except ThreadsAPIError as e:
        print(f"API エラー: {e}", file=sys.stderr)
        sys.exit(1)
    _print_json(data, args.pretty)


def cmd_repost(args: argparse.Namespace) -> None:
    client = _client(args)
    try:
        data = publish.repost(client, args.media_id)
    except ThreadsAPIError as e:
        print(f"API エラー: {e}", file=sys.stderr)
        sys.exit(1)
    _print_json(data, args.pretty)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="threads-kit",
        description="Threads Graph API の基本操作（個人利用・開発モード想定）。",
    )
    parser.add_argument(
        "--token",
        help="アクセストークン（未指定時は環境変数 THREADS_ACCESS_TOKEN）",
    )
    parser.add_argument(
        "--user-path",
        default="me",
        help="API パス上のユーザー ID（通常は me のまま）",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_me = sub.add_parser("me", help="GET /me（プロフィール）")
    p_me.add_argument(
        "--fields",
        default=profile.DEFAULT_ME_FIELDS,
        help="取得フィールド（カンマ区切り）",
    )
    p_me.add_argument("--pretty", action="store_true", help="整形して出力")
    p_me.set_defaults(func=cmd_me)

    p_list = sub.add_parser("threads-list", help="自分のスレッドを 1 行 1 JSON で列挙")
    p_list.add_argument(
        "--fields",
        default=posts.DEFAULT_THREAD_FIELDS,
        help="取得フィールド（カンマ区切り）",
    )
    p_list.add_argument("--limit", type=int, default=0, help="最大件数（0 で無制限）")
    p_list.set_defaults(func=cmd_threads_list)

    p_backup = sub.add_parser("backup", help="自分のスレッド全件を JSON ファイルに保存")
    p_backup.add_argument(
        "--output",
        "-o",
        default="threads_backup.json",
        help="出力ファイルパス",
    )
    p_backup.add_argument(
        "--fields",
        default=posts.DEFAULT_THREAD_FIELDS,
        help="取得フィールド（カンマ区切り）",
    )
    p_backup.add_argument("--pretty", action="store_true", help="JSON をインデント付きで保存")
    p_backup.add_argument("--quiet", "-q", action="store_true", help="進捗ログを出さない")
    p_backup.set_defaults(func=cmd_threads_backup)

    p_ex = sub.add_parser(
        "threads-export-all",
        help="指定ユーザーの全期間スレッドを JSON 配列で取得（ページ間ウェイト・再試行あり）",
    )
    p_ex.add_argument(
        "--output",
        "-o",
        default="threads_all_export.json",
        help="出力先（'-' で標準出力。大量時はメモリに載る点に注意）",
    )
    p_ex.add_argument(
        "--fields",
        default=posts.DEFAULT_THREAD_FIELDS,
        help="取得フィールド（カンマ区切り）",
    )
    p_ex.add_argument(
        "--page-delay",
        type=float,
        default=0.35,
        metavar="SEC",
        help="2 ページ目以降のリクエスト間隔の基準秒（ジッタが加算される）",
    )
    p_ex.add_argument(
        "--page-jitter",
        type=float,
        default=0.25,
        metavar="SEC",
        help="ページ間隔に加えるランダムジッタの上限秒",
    )
    p_ex.add_argument(
        "--max-retries",
        type=int,
        default=12,
        help="同一ページ取得の最大再試行回数（429 / 5xx / レート系 Graph エラー時）",
    )
    p_ex.add_argument(
        "--backoff-initial",
        type=float,
        default=2.0,
        metavar="SEC",
        help="再試行の指数バックオフの初期秒",
    )
    p_ex.add_argument(
        "--backoff-max",
        type=float,
        default=120.0,
        metavar="SEC",
        help="再試行待機の上限秒",
    )
    p_ex.add_argument(
        "--progress-every",
        type=int,
        default=25,
        metavar="N",
        help="N 件ごとに標準エラーへ進捗を表示（0 で無効）",
    )
    p_ex.add_argument(
        "--pretty",
        action="store_true",
        help="整形 JSON（ファイル出力時は全文をメモリに載せます）",
    )
    p_ex.add_argument("--quiet", "-q", action="store_true", help="完了メッセージも抑止")
    p_ex.set_defaults(func=cmd_threads_export_all)

    p_one = sub.add_parser("thread", help="単一スレッド GET /{id}")
    p_one.add_argument("thread_id", help="スレッド（メディア）ID")
    p_one.add_argument(
        "--fields",
        default=posts.DEFAULT_THREAD_FIELDS,
        help="取得フィールド（カンマ区切り）",
    )
    p_one.add_argument("--pretty", action="store_true", help="整形して出力")
    p_one.set_defaults(func=cmd_thread_get)

    p_pt = sub.add_parser("post-text", help="テキスト投稿（コンテナ作成→公開、または auto_publish）")
    src = p_pt.add_mutually_exclusive_group(required=True)
    src.add_argument("-t", "--text", metavar="BODY", help="投稿本文")
    src.add_argument("--file", metavar="PATH", help="本文をファイルから読む")
    src.add_argument("--stdin", action="store_true", help="標準入力から本文を読む")
    p_pt.add_argument(
        "--auto-publish",
        action="store_true",
        help="auto_publish_text で 1 リクエストのみ（公式: テキスト専用）",
    )
    p_pt.add_argument(
        "--wait",
        type=float,
        default=0.0,
        metavar="SEC",
        help="2 段階投稿時、公開前に待つ秒数（画像・動画の目安は公式に従う）",
    )
    p_pt.add_argument("--reply-to", metavar="ID", help="返信先のメディア ID（reply_to_id）")
    p_pt.add_argument("--reply-control", metavar="MODE", help="返信可能範囲（everyone 等）")
    p_pt.add_argument("--link-attachment", metavar="URL", dest="link_attachment", help="リンクプレビュー用 URL")
    p_pt.add_argument("--topic-tag", metavar="TAG", dest="topic_tag", help="トピックタグ")
    p_pt.add_argument("--pretty", action="store_true", help="整形して出力")
    p_pt.set_defaults(func=cmd_post_text)

    p_pi = sub.add_parser("post-image", help="画像投稿（公開 URL の画像を取得して公開）")
    p_pi.add_argument("--url", required=True, dest="image_url", help="画像の公開 URL（JPEG/PNG 等）")
    p_pi.add_argument("--text", "-t", default=None, help="キャプション")
    p_pi.add_argument(
        "--wait",
        type=float,
        default=5.0,
        metavar="SEC",
        help="コンテナ作成から公開まで待つ秒数（既定 5、公式は平均 30 秒と記載のことも）",
    )
    p_pi.add_argument("--alt-text", dest="alt_text", default=None, help="代替テキスト")
    p_pi.add_argument("--pretty", action="store_true", help="整形して出力")
    p_pi.set_defaults(func=cmd_post_image)

    p_pv = sub.add_parser("post-video", help="動画投稿（公開 URL の動画を取得して公開）")
    p_pv.add_argument("--url", required=True, dest="video_url", help="動画の公開 URL")
    p_pv.add_argument("--text", "-t", default=None, help="キャプション")
    p_pv.add_argument("--wait", type=float, default=10.0, metavar="SEC", help="公開前に待つ秒数（既定 10）")
    p_pv.add_argument("--alt-text", dest="alt_text", default=None, help="代替テキスト")
    p_pv.add_argument("--pretty", action="store_true", help="整形して出力")
    p_pv.set_defaults(func=cmd_post_video)

    p_pub = sub.add_parser("publish", help="既存コンテナを threads_publish のみ実行")
    p_pub.add_argument("--creation-id", required=True, help="POST .../threads で返ったコンテナ ID")
    p_pub.add_argument("--wait", type=float, default=0.0, metavar="SEC", help="公開前に待つ秒数")
    p_pub.add_argument("--pretty", action="store_true", help="整形して出力")
    p_pub.set_defaults(func=cmd_publish)

    p_cc = sub.add_parser("container-create", help="メディアコンテナだけ作成（上級者・カルーセル等）")
    p_cc.add_argument("--media-type", required=True, help="TEXT / IMAGE / VIDEO / CAROUSEL 等")
    p_cc.add_argument("--text", "-t", default=None)
    p_cc.add_argument("--image-url", default=None)
    p_cc.add_argument("--video-url", default=None)
    p_cc.add_argument("--reply-to", default=None, dest="reply_to")
    p_cc.add_argument("--reply-control", default=None)
    p_cc.add_argument("--link-attachment", default=None)
    p_cc.add_argument("--topic-tag", default=None)
    p_cc.add_argument("--children", default=None, help="カルーセル用の子コンテナ ID（カンマ区切り）")
    p_cc.add_argument(
        "--is-carousel-item",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="カルーセル要素として作成するか",
    )
    p_cc.add_argument("--auto-publish-text", action="store_true", help="テキストを即時公開（TEXT のみ）")
    p_cc.add_argument("--alt-text", default=None)
    p_cc.add_argument("--quote-post-id", default=None)
    p_cc.add_argument("--pretty", action="store_true", help="整形して出力")
    p_cc.set_defaults(func=cmd_container_create)

    p_cs = sub.add_parser("container-status", help="コンテナの status / error_message を取得")
    p_cs.add_argument("container_id", help="コンテナ ID")
    p_cs.add_argument(
        "--fields",
        default="id,status,error_message",
        help="取得フィールド（カンマ区切り）",
    )
    p_cs.add_argument("--pretty", action="store_true", help="整形して出力")
    p_cs.set_defaults(func=cmd_container_status)

    p_del = sub.add_parser("delete", help="投稿（メディア）を削除")
    p_del.add_argument("media_id", help="削除するスレッドのメディア ID")
    p_del.add_argument("--pretty", action="store_true", help="整形して出力")
    p_del.set_defaults(func=cmd_delete)

    p_rp = sub.add_parser("repost", help="既存投稿をリポスト")
    p_rp.add_argument("media_id", help="リポスト元のメディア ID")
    p_rp.add_argument("--pretty", action="store_true", help="整形して出力")
    p_rp.set_defaults(func=cmd_repost)

    return parser


def main(argv: list[str] | None = None) -> None:
    _try_load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
