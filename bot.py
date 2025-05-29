import discord
import asyncio
import json
import aiohttp
from discord.ext import tasks
from datetime import datetime, timedelta, timezone

# ===== 設定読み込み・保存 =====
CONFIG_PATH = "config.json"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config():
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

config = load_config()

# ===== Discord設定 =====
DISCORD_TOKEN = "YOUR_DISCORD_TOKEN"
CHANNEL_ID = 123456789012345678  # 通知先チャンネルID
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ===== Twitter API設定 =====
BEARER_TOKEN = "YOUR_TWITTER_BEARER_TOKEN"
HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}"
}

# 最後にチェックした時刻（UTC）
last_checked = datetime.now(timezone.utc) - timedelta(seconds=config.get("polling_interval", 60))

def is_admin(user_id):
    return user_id in config.get("admins", [])

async def fetch_tweets():
    global last_checked
    username = config.get("target_user")
    if not username:
        return []

    since_time = last_checked
    last_checked = datetime.now(timezone.utc)

    url = (
        f"https://api.twitter.com/2/tweets/search/recent"
        f"?query=from:{username}"
        f"&tweet.fields=created_at,attachments"
        f"&expansions=attachments.media_keys,referenced_tweets.id,author_id"
        f"&media.fields=preview_image_url,url,type"
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp:
            if resp.status != 200:
                print("Twitter API Error", await resp.text())
                return []
            data = await resp.json()
            tweets = data.get("data", [])

            # フィルタリング: 取得間隔中のツイートだけ
            recent_tweets = []
            for tweet in tweets:
                created_at = datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00"))
                if since_time <= created_at <= last_checked:
                    recent_tweets.append(tweet)

            return recent_tweets

async def send_tweet(tweet):
    tweet_id = tweet["id"]
    url = f"https://twitter.com/{config.get('target_user')}/status/{tweet_id}"
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(url)

@tasks.loop(seconds=60)
async def check_tweets():
    if not config.get("monitoring", True):
        return
    tweets = await fetch_tweets()
    for tweet in reversed(tweets):
        await send_tweet(tweet)

@client.event
async def on_ready():
    print(f"Bot logged in as {client.user}")
    check_tweets.change_interval(seconds=config.get("polling_interval", 60))
    check_tweets.start()

@client.event
async def on_message(message):
    global last_checked

    if message.author.bot:
        return
    content = message.content.strip()

    if content == "!help-twitterbot":
        help_msg = (
            "📘 **Twitter通知Bot コマンド一覧**\n"
            "!help-twitterbot - このメッセージを表示\n"
            "!status - 現在の状態を表示\n"
            "!fetch - 手動でツイートを取得して送信\n"
            "（以下は管理者のみ）\n"
            "!setuser <ユーザー名> - 監視対象ユーザー変更\n"
            "!on - 通知ON\n"
            "!off - 通知OFF\n"
            "!interval <秒> - 取得間隔を変更"
        )
        await message.channel.send(help_msg)

    elif content == "!status":
        status = (
            f"🔎 監視対象: `{config.get('target_user')}`\n"
            f"📡 通知: {'ON' if config.get('monitoring') else 'OFF'}\n"
            f"⏱ 間隔: {config.get('polling_interval', 60)}秒"
        )
        await message.channel.send(status)

    elif content == "!fetch":
        await message.channel.send("⏳ ツイートを取得中...")
        tweets = await fetch_tweets()
        if not tweets:
            await message.channel.send("🚫 新しいツイートはありません。")
        for tweet in reversed(tweets):
            await send_tweet(tweet)

    elif content.startswith("!setuser") and is_admin(message.author.id):
        parts = content.split()
        if len(parts) >= 2:
            config["target_user"] = parts[1]
            save_config()
            await message.channel.send(f"✅ 監視ユーザーを `{parts[1]}` に設定しました。")

    elif content == "!on" and is_admin(message.author.id):
        config["monitoring"] = True
        save_config()
        await message.channel.send("✅ 通知をONにしました。")

    elif content == "!off" and is_admin(message.author.id):
        config["monitoring"] = False
        save_config()
        await message.channel.send("🛑 通知をOFFにしました。")

    elif content.startswith("!interval") and is_admin(message.author.id):
        parts = content.split()
        if len(parts) >= 2 and parts[1].isdigit():
            sec = int(parts[1])
            config["polling_interval"] = sec
            save_config()
            check_tweets.change_interval(seconds=sec)
            await message.channel.send(f"⏱ 取得間隔を {sec} 秒に変更しました。")

            # 最後取得時刻を再設定して、次のチェックで重複取得しないように
            global last_checked
            last_checked = datetime.now(timezone.utc) - timedelta(seconds=sec)

client.run(DISCORD_TOKEN)
