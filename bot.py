import discord
import aiohttp
import asyncio
import json
import datetime

# ==== 設定（トークンを書いてください） ====
DISCORD_TOKEN = "Discordのボットトークン"
BEARER_TOKEN = "Twitterのトークン"
CHANNEL_ID = 1234567890123456  # DiscordチャンネルID（整数）

# ==== 設定ファイルの読み書き ====
CONFIG_FILE = "config.json"

def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

config = load_config()

# ==== Discordクライアント ====
class TwitterBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        
    async def setup_hook(self):
        # バックグラウンドタスクを開始
        self.bg_task = self.loop.create_task(self.notify_tweets())
        print("🚀 Twitterbot バックグラウンドタスクを開始しました")
        
    async def on_ready(self):
        print(f'✅ {self.user} としてログインしました')
        print(f'📡 チャンネルID: {CHANNEL_ID}')
        
    # ==== Twitter API 経由でツイート取得 ====
    async def fetch_tweets(self, username, since_time):
        headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
        url = (
            f"https://api.twitter.com/2/users/by/username/{username}"
            f"?user.fields=id"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                if "data" not in data:
                    print(f"[DEBUG] ユーザー {username} が見つかりません: {data}")
                    return [], {}
                user_id = data["data"]["id"]

            now = datetime.datetime.utcnow()
            # 設定された間隔の期間内のツイートを取得（現在時刻から遡って）
            start_time = (now - datetime.timedelta(seconds=config["polling_interval"])).isoformat("T") + "Z"
            
            print(f"[DEBUG] {username} のツイート取得中...")
            print(f"[DEBUG] 現在時刻: {now.isoformat()}")
            print(f"[DEBUG] 取得開始時刻: {start_time}")
            print(f"[DEBUG] 取得間隔: {config['polling_interval']}秒")
            
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
                print(f"[DEBUG] API レスポンス: {tweets_data}")
                
                if "errors" in tweets_data:
                    print(f"[ERROR] Twitter API エラー: {tweets_data['errors']}")
                    
                tweets = tweets_data.get("data", [])
                includes = tweets_data.get("includes", {})
                media_map = {m["media_key"]: m for m in includes.get("media", [])}
                
                print(f"[DEBUG] 取得したツイート数: {len(tweets)}")
                for tweet in tweets:
                    created_at = tweet.get("created_at", "")
                    text_preview = tweet.get("text", "")[:50] + "..." if len(tweet.get("text", "")) > 50 else tweet.get("text", "")
                    print(f"[DEBUG] ツイート: {created_at} - {text_preview}")
                
                return tweets, media_map

    # ==== 通知処理 ====
    async def notify_tweets(self):
        await self.wait_until_ready()
        channel = self.get_channel(CHANNEL_ID)
        
        if not channel:
            print(f"❌ エラー: チャンネルID {CHANNEL_ID} が見つかりません")
            return
            
        print("🔄 ツイート監視を開始しました")
        
        while not self.is_closed():
            if config.get("monitoring", False):
                for username in config.get("target_users", []):
                    try:
                        tweets, media_map = await self.fetch_tweets(username, config["polling_interval"])
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
    async def on_message(self, message):
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
                "`!interval 秒数` - 取得間隔を変更（管理者）\n"
                "`!admin 追加/削除 ユーザーID` - 管理者の追加/削除（管理者）"
            )
            await message.channel.send(help_text)

        elif content == "!status":
            status = "ON ✅" if config.get("monitoring") else "OFF ❌"
            users = ", ".join(config.get("target_users", [])) or "未設定"
            interval = config.get("polling_interval", 60)
            admins = ", ".join([f"<@{admin_id}>" for admin_id in config.get("admins", [])]) or "未設定"
            await message.channel.send(
                f"**Botステータス:** {status}\n**監視ユーザー:** {users}\n**取得間隔:** {interval}秒\n**管理者:** {admins}"
            )

        elif content == "!fetch":
            await message.channel.send("⏳ ツイートを取得中...")
            for username in config.get("target_users", []):
                try:
                    tweets, media_map = await self.fetch_tweets(username, config["polling_interval"])
                    if not tweets:
                        await message.channel.send(f"{username}：新しいツイートはありません。")
                        continue
                    for tweet in reversed(tweets):
                        text = tweet.get("text", "")
                        url = f"https://twitter.com/{username}/status/{tweet['id']}"
                        content_msg = f"**{username} の新しいツイート**\n{text}\n{url}"
                        if "attachments" in tweet and "media_keys" in tweet["attachments"]:
                            for key in tweet["attachments"]["media_keys"]:
                                media = media_map.get(key)
                                if media and media["type"] in ["photo", "video"]:
                                    content_msg += f"\n{media.get('url', media.get('preview_image_url', ''))}"
                        await message.channel.send(content_msg)
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
                if sec < 60:
                    await message.channel.send("⚠️ 間隔は60秒（1分）以上で設定してください。Twitter API制限のため。")
                    return
                config["polling_interval"] = sec
                save_config(config)
                await message.channel.send(f"⏱ 取得間隔を {sec} 秒に設定しました。")
            except (IndexError, ValueError):
                await message.channel.send("⚠️ 正しい秒数を指定してください。例: `!interval 3600`")

        elif content.startswith("!admin") and is_admin:
            parts = content.split()
            if len(parts) < 3:
                await message.channel.send("⚠️ 使用方法: `!admin 追加/削除 ユーザーID`")
                return
            
            action = parts[1]
            try:
                user_id = int(parts[2])
            except ValueError:
                await message.channel.send("⚠️ 有効なユーザーIDを指定してください。")
                return
            
            if action == "追加":
                if user_id not in config.get("admins", []):
                    config.setdefault("admins", []).append(user_id)
                    save_config(config)
                    await message.channel.send(f"✅ <@{user_id}> を管理者に追加しました。")
                else:
                    await message.channel.send("⚠️ このユーザーは既に管理者です。")
            elif action == "削除":
                if user_id in config.get("admins", []):
                    config["admins"].remove(user_id)
                    save_config(config)
                    await message.channel.send(f"✅ <@{user_id}> を管理者から削除しました。")
                else:
                    await message.channel.send("⚠️ このユーザーは管理者ではありません。")
            else:
                await message.channel.send("⚠️ '追加' または '削除' を指定してください。")

# ==== 起動 ====
async def main():
    client = TwitterBot()
    try:
        await client.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Botを停止しています...")
        await client.close()
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Botを終了しました")