# vigilant-robot

# 📡 Twitter → Discord 通知Bot

このBotは、指定されたTwitterユーザーのツイートを定期的に取得し、Discordに自動で通知するBotです。

---

## 📁 構成ファイル一覧

project/
├── bot.py # メインのBotスクリプト
├── config.json # 設定ファイル（永続化）
├── .env # 認証トークンなどを記載
└── README.md # このファイル


---

## 🔐 `.env` ファイルの内容

プロジェクトのルートに `.env` ファイルを作成し、以下のように記述します：

```env
DISCORD_TOKEN=your_discord_bot_token
BEARER_TOKEN=your_twitter_bearer_token
CHANNEL_ID=123456789012345678  # 通知を送るDiscordチャンネルID

⚙️ config.json

Botの動作設定ファイルです（コマンドで変更可能、起動時に読み込まれます）：

{
  "target_user": "twitteruser",            // 監視対象（@なし）
  "monitoring": true,                      // 通知ON/OFF
  "polling_interval": 60,                  // ツイート取得間隔（秒）
  "admins": [123456789012345678]           // 管理者のDiscordユーザーID
}

📦 依存パッケージ

Python 3.12+ 対応済み。以下のライブラリをインストール：

pip install discord.py aiohttp python-dotenv

🚀 起動手順

    .env にトークンとチャンネルIDを記述

    config.json を作成

    パッケージをインストール

    以下で起動：

python bot.py

🛠 コマンド一覧（Discord内）
コマンド	権限	内容
!help-twitterbot	全員	コマンド一覧を表示
!status	全員	現在の設定状態を表示
!fetch	全員	手動でツイート取得
!setuser <ユーザー名>	管理者	監視ユーザーを変更
!on	管理者	通知をONにする
!off	管理者	通知をOFFにする
!interval <秒数>	管理者	取得間隔を設定（例：!interval 300）
🔄 動作仕様

    取得間隔内に投稿されたツイートのみ取得・送信。

    初回起動でも過去全件取得は行われず、現在時刻を基準に取得。

    ツイートが複数ある場合もすべてDiscordに通知。

    重複通知は発生しません（時間フィルタにより制御）。

📌 注意事項

    複数アカウント監視や複数チャンネル通知は未対応（今後拡張可能）。

    管理者はDiscordの「ユーザーID」で指定（右クリック→IDコピー）。

    .env は .gitignore に追加して、公開リポジトリでは管理しないでください。

🧪 テスト方法

    !fetch を使えば即時に最新ツイートを取得・通知可能です。

    config.json を手動編集した後はBotの再起動が必要です。