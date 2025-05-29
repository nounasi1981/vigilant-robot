import discord
import aiohttp
import asyncio
import json
import datetime

# ==== 設定（トークン直書き） ====
DISCORD_TOKEN = "あなたのDiscord Botトークン"
BEARER_TOKEN = "あなたのTwitter API Bearerトークン"
CHANNEL_ID = 123456789012345678  # DiscordチャンネルID（整数）

# ==== 設定ファイルの読み書き ====
CONFIG_FILE = "config.json"

def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

config = load_config()

# ==== Discordクライアント ====
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ==== Twitter API 経由でツイート取得 ====
async def fetch_tweets(username, since_time):
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    url = (
        f"https://api.twitter.com/2/users/by/username/{username}"
        f"?user.fields=id"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            if "data" not in data:
                return []
            user_id = data["data"]["id"]

        now = datetime.datetime.utcnow()
        start_time = (now - datetime.timedelta(seconds=config["polling_interval"])).isoformat("T") + "Z"
        timeline_url = (
            f"https://api.twitter.com/2/users/{user_id}/tweets"
            f"?tweet.fields=created_at,referenced_tweets,attachments"
            f"&expansions=attachments.media_keys,referenced_tweets.id,referenced_tweets.id.author_id"
            f"&media.fields=url,preview_image_url,type"
            f"&start_time={start_time}"
            f"&exclude=replies"
        )
        async with session.get(timeline_url, headers=headers) as resp:
            tweets_data = await resp.json()
            tweets = tweets_data.get("data", [])
            includes = tweets_data.get("includes", {})
            media_map = {m["media_key"]: m for m in includes.get("media", [])}
            return tweets, media_map

# ==== 通知処理 ====
async def notify_tweets():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    while not client.is_closed():
        if config.get("monitoring", False):
            for username in config.get("target_users", []):
                try:
                    tweets, media_map = await fetch_tweets(username, config["polling_interval"])
                    for tweet in reversed(tweets):  # 時系列順に
                        text = tweet.get("text", "")
                        url = f"https://twitter.com/{username}/status/{tweet['id']}"
                        content = f"**{username} の新しいツイート**\n{text}\n{url}"
                        files = []
                        if "attachments" in tweet and "media_keys" in tweet["attachments"]:
                            for key in tweet["attachments"]["media_keys"]:
                                media = media_map.get(key)
                                if media and media["type"] in ["photo", "video"]:
                                    content += f"\n{media.get('url', media.get('preview_image_url', ''))}"
                        await channel.send(content)
                except Exception as e:
                    print(f"[ERROR] {username} のツイート取得に失敗: {e}")
        await asyncio.sleep(config["polling_interval"])

# ==== 管理コマンド ====
@client.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()
    is_admin = message.author.id in config.get("admins", [])

    if content == "!help-twitterbot":
        help_text = (
            "**🛠 コマンド一覧:**\n"
            "`!help-twitterbot` - このヘルプを表示\n"
            "`!status` - 現在の設定状況を表示\n"
            "`!fetch` - 手動でツイート取得\n"
            "`!on` / `!off` - 通知の有効化/無効化（管理者）\n"
            "`!setuser ユーザー1 ユーザー2 ...` - 監視ユーザーを設定（管理者）\n"
            "`!interval 秒数` - 取得間隔を変更（管理者）"
        )
        await message.channel.send(help_text)

    elif content == "!status":
        status = "ON ✅" if config.get("monitoring") else "OFF ❌"
        users = ", ".join(config.get("target_users", []))
        interval = config.get("polling_interval", 60)
        await message.channel.send(
            f"**Botステータス:** {status}\n**監視ユーザー:** {users}\n**取得間隔:** {interval}秒"
        )

    elif content == "!fetch":
        await message.channel.send("⏳ ツイートを取得中...")
        for username in config.get("target_users", []):
            try:
                tweets, media_map = await fetch_tweets(username, config["polling_interval"])
                if not tweets:
                    await message.channel.send(f"{username}：新しいツイートはありません。")
                    continue
                for tweet in reversed(tweets):
                    text = tweet.get("text", "")
                    url = f"https://twitter.com/{username}/status/{tweet['id']}"
                    content = f"**{username} の新しいツイート**\n{text}\n{url}"
                    if "attachments" in tweet and "media_keys" in tweet["attachments"]:
                        for key in tweet["attachments"]["media_keys"]:
                            media = media_map.get(key)
                            if media and media["type"] in ["photo", "video"]:
                                content += f"\n{media.get('url', media.get('preview_image_url', ''))}"
                    await message.channel.send(content)
            except Exception as e:
                await message.channel.send(f"⚠️ {username} の取得中にエラーが発生しました: {e}")

    elif content == "!on" and is_admin:
        config["monitoring"] = True
        save_config(config)
        await message.channel.send("✅ 通知を有効にしました。")

    elif content == "!off" and is_admin:
        config["monitoring"] = False
        save_config(config)
        await message.channel.send("🛑 通知を無効にしました。")

    elif content.startswith("!setuser") and is_admin:
        users = content.split()[1:]
        if not users:
            await message.channel.send("⚠️ ユーザー名を指定してください。")
            return
        config["target_users"] = users
        save_config(config)
        await message.channel.send(f"✅ 監視ユーザーを更新しました：{', '.join(users)}")

    elif content.startswith("!interval") and is_admin:
        try:
            sec = int(content.split()[1])
            config["polling_interval"] = sec
            save_config(config)
            await message.channel.send(f"⏱ 取得間隔を {sec} 秒に設定しました。")
        except:
            await message.channel.send("⚠️ 正しい秒数を指定してください。")

# ==== 起動 ====
client.loop.create_task(notify_tweets())
client.run(DISCORD_TOKEN)
