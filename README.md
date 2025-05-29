# vigilant-robot

# 📡 Twitter → Discord 通知Bot

このBotは、指定したTwitterユーザーのツイートを定期的に取得し、Discordチャンネルに自動で投稿するBotです。

---

## 📁 ファイル構成

project/
├── bot.py # メインのBotスクリプト（トークン等を直書き）
├── config.json # 設定ファイル（監視ユーザー・状態・間隔など）
└── README.md # このファイル


---

## 🔐 トークンの設定方法

`bot.py` の先頭付近で以下のようにトークンなどを直接記述してください：

```python
DISCORD_TOKEN = "あなたのDiscord Botトークン"
BEARER_TOKEN = "あなたのTwitter API Bearerトークン"
CHANNEL_ID = 123456789012345678  # 通知を送るDiscordチャンネルID（整数で記述）

⚙️ config.json の例

{
  "target_user": "twitteruser",            // 監視対象のTwitterユーザー名（@なし）
  "monitoring": true,                      // 通知ON/OFF
  "polling_interval": 60,                  // 取得間隔（秒）
  "admins": [123456789012345678]           // 管理者ユーザーIDの配列（整数）
}

    admins で指定されたDiscordユーザーのみがBotの管理コマンドを使用できます。

📦 インストールが必要なパッケージ

以下をインストールしてください：

pip install discord.py aiohttp

🚀 Botの起動方法

    bot.py にトークンなどを記入

    config.json を作成

    必要なパッケージをインストール

    Botを起動：

python bot.py

💬 使用可能なコマンド一覧
コマンド	権限	内容
!help-twitterbot	全員	コマンド一覧を表示
!status	全員	現在の監視設定とステータスを表示
!fetch	全員	手動でTwitter投稿を即時取得・通知
!setuser <ユーザー名>	管理者	監視するTwitterユーザーを変更
!on	管理者	通知をONにする
!off	管理者	通知をOFFにする
!interval <秒数>	管理者	ツイート取得間隔を変更（例：!interval 300）
🔄 動作仕様

    指定された「取得間隔（秒）」に基づき、その時間内に投稿されたツイートのみを取得。

    初回起動時にも過去すべての投稿は取得されず、過去◯秒以内に限定。

    重複送信はありません。

    間隔中に複数投稿があった場合も、すべて通知されます。

📌 注意事項

    管理者は Discord の「ユーザーID」で指定（開発者モードでコピー）。

    bot.py にトークンを直書きするため、ソースの取り扱いには注意してください。

    公開リポジトリなどにアップロードしないようにしましょう。

🧪 テスト方法

    !fetch コマンドで即時にツイート取得テストができます。

    config.json を手動で編集した場合は、Botの再起動が必要です。
