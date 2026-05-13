# Threads API 基本操作キット

Threads Graph API（`https://graph.threads.net/v1.0`）を、個人のバックアップや検証用にさっと触るための最小構成です。

## できること

| 操作 | CLI | Python |
|------|-----|--------|
| 自分のプロフィール | `threads-kit me` | `profile.get_me(client)` |
| 自分のスレッド列挙 | `threads-kit threads-list` | `posts.iter_my_threads(client)` |
| 全件バックアップ（JSON） | `threads-kit backup` | `posts.fetch_all_my_threads(client)` |
| **全期間エクスポート（レート配慮）** | **`threads-kit threads-export-all`** | **`posts.iter_user_threads` + `export_threads_json_array_stream`** |
| 1 件取得 | `threads-kit thread <ID>` | `posts.get_thread(client, id)` |
| テキスト投稿 | `threads-kit post-text …` | `publish.publish_text_post(client, …)` |
| 画像・動画投稿 | `post-image` / `post-video` | `publish.publish_image_post` など |
| コンテナだけ作成 | `container-create` | `publish.create_threads_container` |
| 公開（2 段階目） | `publish --creation-id` | `publish.publish_container` |
| コンテナ状態 | `container-status <ID>` | `publish.get_container_status` |
| 削除・リポスト | `delete` / `repost` | `publish.delete_media` / `publish.repost` |

---

## 使い方（手順）

大きく **Meta 開発者コンソールでの準備（セクション 0）** と **このリポジトリを動かす手順（セクション 1 以降）** に分かれます。

### 0. Meta 開発者コンソールでの準備（初回だけ）

このキットは **Graph Threads API** にそのまま HTTP で繋ぎます。最初に [Meta for Developers](https://developers.facebook.com/) でアプリと権限を整え、**自分の Threads アカウント用のユーザーアクセストークン**を用意してください。画面のラベルは更新されることがあるため、見当たらない項目は公式ドキュメントのスクリーンショットや文言に合わせて読み替えてください。

#### 0-1. 開発者としてログインする

1. ブラウザで [developers.facebook.com](https://developers.facebook.com/) を開き、Facebook 開発者アカウントでログインします。  
2. 初回は開発者登録の同意や電話番号確認などが求められることがあります。表示に従って完了させます。

#### 0-2. アプリを作成する（Threads API）

1. ダッシュボードで **「アプリを作成」** を選びます。  
2. ユースケースの選択で **「Threads API にアクセス」**（または同等の Threads 向けの項目）を選びます。  
3. アプリ名・連絡用メールを入力して作成します。アプリ名に `Threads` や `Meta` が含まれるとポリシーで弾かれる場合があるため、分かりやすい独自名にするとよいです。  
4. 作成後、左メニューから **Threads** プロダクトが有効になっているか確認し、セットアップウィザードがあれば完了させます。

#### 0-3. スコープ（アクセス許可）を確認する

アプリの **ユースケース** または **Threads → アクセス許可と機能** などから、少なくとも次のような権限が付いているか確認します（必要に応じて追加・審査が必要なものもあります）。

- 自分のプロフィールや投稿を読む用途では、例として **`threads_basic`** がよく使われます。  
- **API から新規投稿・削除・リポスト**などを行うには、別途 **`threads_content_publish`**（およびトークン発行時にその許可を付与）が必要です。詳しくは [Publishing](https://developers.facebook.com/docs/threads/reference/publishing) と [Posts](https://developers.facebook.com/docs/threads/posts) を参照してください。  
- 返信の読み取りなどを行う場合は、別途 **`threads_read_replies`** などが必要になることがあります。

#### 0-4. Threads テスターを追加する（ここが「自分の垢」を紐づける所）

**開発モード**のアプリでは、登録した **Threads テスター**のアカウントに限り、ユーザーアクセストークンでデータを取得できます。

1. 開発者コンソールの左メニューで **「アプリの役割」** を開きます。  
2. その中の **「Threads テスター」**（名前は多少異なる場合があります）を選びます。  
3. **「メンバーを追加」** などのボタンから、**データを取得したい Threads のユーザー名**（`@` なしの ID）を検索して追加します。

よくある混同として、**「テストユーザー」**（Facebook のダミー個人アカウントを作る画面）があります。これは Graph API 全般の検証用で、**今回の「自分の Threads 投稿をバックアップする」目的では通常は不要**です。必要なのは上記の **Threads テスター**への追加です。

#### 0-5. Threads（または Instagram）側で招待を承認する

テスターを追加しただけでは **承認待ち**のままです。取得したい本人のアカウントで次を行います。

1. スマートフォンまたはブラウザで **Threads**（必要に応じて **Instagram** の設定経由）を開きます。  
2. **設定** → **ウェブサイトのアクセス許可**（または類似の名称）を開きます。  
3. **「招待」** の一覧に、作成したアプリ名が出ているので **承認**します。

開発者コンソールの Threads テスター一覧で、対象ユーザーが承認済みになっているか確認できると安心です。

#### 0-6. ユーザーアクセストークンを発行する

1. アプリの **ユースケース** から **Threads API** の行を選び、**カスタマイズ**や**編集**などで詳細画面を開きます。  
2. 左またはタブで **「設定」** に切り替えます（「アクセス許可と機能」だけ見て終わらないように注意してください）。  
3. **「Threads テスター」** の一覧に、先ほど承認したユーザーが表示されていることを確認し、その横の **「トークンを生成」**（`Generate Token`）を押します。  
4. ログインや追加の同意画面が出たら進め、表示された **長い文字列をコピー**します。再表示できないことが多いので、すぐにパスワードマネージャや `.env`（未コミット）に保存してください。

このトークンが、このリポジトリの **`THREADS_ACCESS_TOKEN`** に相当します。他人に見せたり、チャットやスクショに写したりしないでください。

#### 0-7. 開発モードで押さえておくこと

- **一般公開していないアプリ**では、Threads テスターに登録したアカウント以外のデータは取得できません。  
- 本番公開や審査は別プロセスになります。個人のバックアップ用途なら開発モードのままで足りることが多いです。  
- Meta 側の UI や API の仕様は変わり得ます。エラーが続くときは [Threads API の公式ドキュメント](https://developers.facebook.com/docs/threads) をあたり、スコープ・テスター・トークンの有効期限を確認してください。

---

### 1. リポジトリに移動する

```bash
cd /path/to/this/repo
```

`this/repo` は、このプロジェクトを置いたディレクトリに読み替えてください。

### 2. Python の仮想環境を作る

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows（コマンドプロンプト）**

```bash
python -m venv .venv
.venv\Scripts\activate.bat
```

**Windows（PowerShell）**

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
```

以降、プロンプトの先頭に `(.venv)` などが付いていれば仮想環境が有効です。

### 3. パッケージをインストールする

このリポジトリを **編集可能モード**で入れると、`threads-kit` コマンドが使えます。

```bash
pip install -U pip
pip install -e .
```

（`pip install -r requirements.txt` だけでも依存ライブラリは入りますが、その場合は `threads-kit` が PATH に無いことがあるので、通常は上の `pip install -e .` を推奨します。）

### 4. アクセストークンを渡す

次のいずれかで大丈夫です。

**方法 A: 環境変数（シェルごとに設定）**

```bash
export THREADS_ACCESS_TOKEN='ここに長いトークン文字列'
```

任意で API のベース URL を変えるとき:

```bash
export THREADS_GRAPH_BASE_URL='https://graph.threads.net/v1.0'
```

**方法 B: `.env` ファイル（おすすめ）**

1. リポジトリ直下の **`.env.example`** をコピーして `.env` を作る  

   ```bash
   cp .env.example .env
   ```

2. `.env` を開き、`THREADS_ACCESS_TOKEN=` の右側に実トークンを貼る（引用符は不要な場合が多いですが、値に `#` や空白が含まれるときは引用符で囲んでください）。

3. 必要なら `.env.example` にコメントのある **任意変数**（例: `THREADS_GRAPH_BASE_URL`）も `.env` にコピーして調整します。未設定のときは公式の既定 URL（`https://graph.threads.net/v1.0`）が使われます。

CLI 起動時に `python-dotenv` が `.env` を読み込みます。

**方法 C: direnv を使う場合**

[direnv](https://direnv.net/) でディレクトリに入ったときだけ環境を載せたい場合は、**`.envrc.example`** を参考にします。

```bash
cp .envrc.example .envrc
```

`.envrc` は秘密を書かず、上記のとおり `.env` にトークンを置き、`.envrc` 内では `dotenv_if_exists` で `.env` を読み込む構成が安全です。編集後は `direnv allow` を忘れずに実行してください。

### 5. 動作確認する

まずプロフィールが取れるか確認します。

```bash
threads-kit me --pretty
```

JSON が表示されれば、トークンとアプリ設定は一通りつながっています。

### 6. よく使う操作

**直近だけ流し見する（1 行 1 JSON）**

```bash
threads-kit threads-list --limit 10
```

**自分の投稿をまとめて JSON 保存する**

```bash
threads-kit backup -o threads_backup.json --pretty
```

進捗を表示したくない場合は `-q` を付けます。

```bash
threads-kit backup -o threads_backup.json --pretty -q
```

**全期間の投稿を、レート制限を避けやすい設定で JSON 配列にまとめる**（ページ間にウェイトとジッタ、429 / 5xx / Graph のレート系エラーで指数バックオフ＋再試行。ファイル出力かつ非 `--pretty` なら配列をストリーム書き込み）

```bash
threads-kit threads-export-all -o threads_all_export.json
threads-kit --user-path me threads-export-all -o out.json --page-delay 0.6 --page-jitter 0.3
threads-kit threads-export-all -o - --pretty
```

件数が多いときは `--pretty` や `-o -`（標準出力）はメモリ使用量が増えます。大規模アーカイブには非 pretty のファイル出力を推奨します。より速く取りたいだけなら上の **`backup`** で十分な場合があります（スロットリング無しのため API 制限に触れやすい点に注意）。

**1 件だけ取得する**（ID は API のレスポンスに出てくる `id` など）

```bash
threads-kit thread スレッドのメディアID --pretty
```

トークンをコマンドに直接書く場合（共有 PC では非推奨）:

```bash
threads-kit me --pretty --token 'トークン文字列'
```

**グローバルオプション**（`--token` や `--user-path`）は、サブコマンドの **前** に書きます。

```bash
threads-kit --user-path me post-text -t 'こんにちは' --pretty
```

**テキストを新規投稿する**（既定は「コンテナ作成 → `threads_publish`」の 2 段階。公式どおり `--wait` で間に待てます）

```bash
threads-kit post-text -t 'API からのテスト投稿' --pretty
threads-kit post-text -t 'すぐ公開' --wait 2 --pretty
```

**テキストを 1 リクエストで公開する**（`auto_publish_text`。公式上はテキスト専用）

```bash
threads-kit post-text -t '1 発で投稿' --auto-publish --pretty
```

**ファイルや標準入力から本文を渡す**

```bash
threads-kit post-text --file ./draft.txt --pretty
echo 'パイプで渡す' | threads-kit post-text --stdin --pretty
```

**画像・動画を投稿する**（`image_url` / `video_url` は **Threads が取得できる公開 URL** である必要があります）

```bash
threads-kit post-image --url 'https://example.com/image.jpg' -t 'キャプション' --pretty
threads-kit post-video --url 'https://example.com/movie.mp4' --wait 30 --pretty
```

**返信やリンク付きテキスト**（パラメータは [Publishing リファレンス](https://developers.facebook.com/docs/threads/reference/publishing) に準拠）

```bash
threads-kit post-text -t '返信です' --reply-to 親メディアのID --pretty
threads-kit post-text -t '本文' --link-attachment 'https://example.com/' --pretty
```

**コンテナだけ作ってから、別タイミングで公開する**

```bash
threads-kit container-create --media-type TEXT -t '下書きコンテナ' --pretty
threads-kit publish --creation-id コンテナのID --wait 5 --pretty
```

**コンテナの処理状態を確認する**

```bash
threads-kit container-status コンテナのID --pretty
```

**投稿を削除する・リポストする**

```bash
threads-kit delete メディアID --pretty
threads-kit repost メディアID --pretty
```

### 7. `fetch_threads.py` でバックアップする（互換）

昔どおりスクリプト名で叩きたい場合は、リポジトリ直下で次のとおりです。

```bash
python fetch_threads.py
```

`threads-kit backup` に渡すオプションを、そのまま後ろに続けられます。

```bash
python fetch_threads.py -o my_backup.json --pretty
```

### 8. モジュールとして使う

仮想環境を有効にしたうえで、同じ環境の Python から import します。

```python
import os
from threads_kit import ThreadsGraphClient
from threads_kit import posts, profile, publish

client = ThreadsGraphClient(os.environ["THREADS_ACCESS_TOKEN"])
print(profile.get_me(client))
print(
    publish.publish_text_post(
        client,
        "Python からのテスト",
        auto_publish=True,
    )
)
for row in posts.iter_my_threads(client):
    print(row["id"], row.get("text", "")[:80])

# 全期間をゆっくり取得（ページ間ウェイト・再試行付き）
# for row in posts.iter_user_threads(client, page_delay_seconds=0.5):
#     print(row["id"])
```

---

## CLI 一覧（短いリファレンス）

```bash
threads-kit me --pretty
threads-kit threads-list --limit 10
threads-kit backup -o threads_backup.json --pretty
threads-kit threads-export-all -o threads_all.json
threads-kit thread 1234567890 --pretty
threads-kit post-text -t 'hello' --pretty
threads-kit post-text -t 'fast' --auto-publish --pretty
threads-kit post-image --url 'https://example.com/a.jpg' --pretty
threads-kit publish --creation-id CONTAINER_ID --wait 5 --pretty
threads-kit container-status CONTAINER_ID --pretty
threads-kit delete MEDIA_ID --pretty
threads-kit repost MEDIA_ID --pretty
python -m threads_kit --help
```

---

## 注意

- リポジトリに含めるのは **`.env.example`** と **`.envrc.example`** のような「テンプレート」だけにし、実トークンが入った **`.env`** や **`.envrc`**（秘密を直書きした場合）はコミットしないでください。
- API 経由の投稿には **24 時間あたり 250 件** などのレート制限があります（[Overview](https://developers.facebook.com/docs/threads/overview) 参照）。
- `.gitignore` で `.env` と `threads_backup.json` を除外していますが、別名で保存したファイルは誤コミットに注意してください。
