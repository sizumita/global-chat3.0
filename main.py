"""
チャンネル保存はpickleで行く
"""
import asyncio
import pickle
import re

import aiohttp
import discord
from discord import Webhook

from manager import SQLManager

invite_compile = re.compile("(?:https?://)?discord(?:app\.com/invite|\.gg)/?[a-zA-Z0-9]+/?")


def save_ban_members(_list: list):
    with open("ban.txt", "w") as f:
        f.write(",".join([str(i) for i in _list]))


def load_ban_members():
    try:
        with open("ban.txt", "r") as f:
            return [int(i) for i in f.read().split(",")[:-1]]
    except FileNotFoundError:
        return []


def save_channel_webhook(_dict):
    with open("channels.pickle", "wb") as f:
        pickle.dump(_dict, f)


def load_channel_webhook():
    try:
        with open("channels.pickle", "rb") as f:
            data = pickle.load(f)
    except FileNotFoundError:
        # raise
        return {"global-chat": {}, "global-r18": {}}
    return data


class MyClient(discord.Client):
    def __init__(self, **options):
        super().__init__(**options)
        self.webhooks = load_channel_webhook()
        self.bans = load_ban_members()
        self.manager = SQLManager()
        self.channels = {}
        for key, value in self.webhooks.items():
            for k in list(value):
                self.channels[k] = key

    async def limit_ban(self, message, times, reason):
        self.bans.append(message.author.id)
        await message.channel.send(f"{message.author.mention}, あなたは{reason}ため、制限時間付きbanを受けました。制限時間は{times}分です。")
        user = self.get_user(212513828641046529)
        await user.send(
            f"{message.author.mention}({message.author.name},{message.author.id})は{reason}ため、制限時間付きbanを受けました。制限時間は{times}分です。")
        await asyncio.sleep(times * 60)
        self.bans.remove(message.author.id)

    def end(self):
        save_channel_webhook(self.webhooks)

    async def send_global_message(self, message: discord.Message, name):
        channel = message.channel
        author = message.author
        content = message.clean_content
        message_id_list = [message.id]
        channel_id_list = [message.channel.id]
        if re.search(invite_compile, message.content):
            self.loop.create_task(self.limit_ban(message, 60, "招待を送信しようとした"))
            return
        if message.mention_everyone:
            self.loop.create_task(self.limit_ban(message, 60, "everyoneメンションを送信しようとした"))
            return
        if len(content) > 1000:
            self.loop.create_task(self.limit_ban(message, 60, "1000文字以上の文字を送信しようとした"))
            return
        cat = ""
        if message.attachments:
            embed = discord.Embed()
            embed.set_image(url=message.attachments[0].url)
        else:
            embed = None
        for key, value in self.webhooks.items():
            for k, v in value.items():
                if k == channel.id:
                    cat = key
                    break
        for key, value in self.webhooks[cat].items():
            if message.channel.id == key:
                continue

            async def send(webhook_url):
                try:
                    async with aiohttp.ClientSession() as session:
                        webhook = Webhook.from_url(webhook_url, adapter=discord.AsyncWebhookAdapter(session))
                        # webhook._adapter.store_user = webhook._adapter._store_user
                        result = await webhook.send(
                            content=content,
                            username=author.name,
                            avatar_url=author.avatar_url,
                            wait=True,
                            embed=embed,
                        )
                        message_id_list.append(result.id)
                        channel_id_list.append(key)
                except discord.errors.NotFound:
                    return

            self.loop.create_task(send(value))
        await asyncio.sleep(2)
        await self.manager.save(message, channel_id_list, message_id_list, content)

    async def send_global_notice(self, name="global-chat", text="", title="", mode="normal", **kwargs):
        if mode == "normal":
            embed = discord.Embed(title=title if title else "お知らせ", description=text, color=0x00bfff)

        elif mode == "error":
            embed = discord.Embed(title=title if title else "エラー", description=text, color=0xff0000)

        elif mode == "update":
            embed = discord.Embed(title=title if title else "アップデート", description=text, color=0x00ff00)
            for value in kwargs['_list']:
                for x in range(1, len(kwargs['_list'])):
                    embed.add_field(name=str(x), value=value)

        for channel, webhooks in self.webhooks.items():
            if channel != name:
                continue
            for _id, webhook in webhooks.items():
                async def send(webhook_url):
                    try:
                        async with aiohttp.ClientSession() as session:
                            webhook = Webhook.from_url(webhook_url, adapter=discord.AsyncWebhookAdapter(session))
                            # webhook._adapter.store_user = webhook._adapter._store_user
                            await webhook.send(
                                username=self.user.name,
                                avatar_url=self.user.avatar_url,
                                embed=embed,

                            )
                    except discord.errors.NotFound:
                        return

                self.loop.create_task(send(webhook))
        return

    def user_check(self, message):
        if message.author.id == 212513828641046529:
            return 0
        if message.guild.owner.id == message.author.id:
            return 1
        if message.author.guild_permissions.manage_channels:
            return 2
        return 3

    def check(self, message: discord.Message):
        if message.author.id in self.bans:
            return False
        if message.author.bot:
            return False
        return True

    async def add_channel_global(self, message: discord.Message, name):
        webhooks = await message.channel.webhooks()
        if webhooks:
            webhook = webhooks[0]
        else:
            try:
                webhook = await message.channel.create_webhook(name='global-chat')
            except Exception:
                await message.channel.send(f"{message.author.mention}, 権限がありません！")
                return
        self.webhooks[name][message.channel.id] = webhook.url
        self.channels[message.channel.id] = name
        self.loop.create_task(self.send_global_notice(name, f"{message.guild.name} がコネクトしました。"))

    def get_member_id_from_name(self, name):
        for member in self.get_all_members():
            if member.name == name:
                return member.id

    async def on_message(self, message: discord.Message):
        if not self.check(message):
            return
        if message.content.startswith(">"):
            await self.command(message)
            return

        if message.channel.id in self.channels.keys():
            await self.send_global_message(message, self.channels[message.channel.id])

    async def command(self, message: discord.Message):
        try:
            command, args = message.content.split(" ")[0], message.content.split(" ")[1:]
        except IndexError:
            command = message.content
            args = []
        if command == ">connect":
            if not self.user_check(message) <= 2:
                return
            if not args:
                if not message.channel.id in self.webhooks['global-chat']:
                    self.loop.create_task(self.add_channel_global(message, "global-chat"))

            else:
                if args[0] == "global-r18":
                    if not message.channel.is_nsfw():
                        await message.channel.send("NSFW指定をしてください。")
                        return
                    self.loop.create_task(self.add_channel_global(message, "global-r18"))
                elif args[0] in self.webhooks.keys():
                    self.loop.create_task(self.add_channel_global(message, args[0]))
        elif command == ">disconnect":
            if not self.user_check(message) <= 2:
                return
            category = False
            for key, value in self.webhooks.items():
                if message.channel.id in value.keys():
                    category = key
                    break
            if not category:
                return
            del self.webhooks[category][message.channel.id]
            del self.channels[message.channel.id]
            await message.channel.send("接続解除しました。")

        elif command == ">s":
            try:
                channel_id, message_id = await self.manager.get_message_ids(int(args[0]))
                if not channel_id:
                    return
            except Exception:
                raise
            channel = self.get_channel(channel_id)
            _message: discord.Message = await channel.fetch_message(message_id)
            embed = discord.Embed(title=f"id:{int(args[0])}のデータ", description=_message.content, color=0x00bfff,
                                  timestamp=_message.created_at)
            embed.set_author(name=_message.author.name, icon_url=_message.author.avatar_url)
            embed.set_footer(text=f"{_message.guild.name}", icon_url=_message.guild.icon_url)
            await message.channel.send(embed=embed)
        elif command == ">del":
            if not self.user_check(message) == 0:
                return
            if not args:
                return
            _id = self.get_member_id_from_name(args[0])
            messages = await self.manager.get_messages(_id, self)
            for m in messages:
                try:
                    await m.delete()
                except discord.Forbidden:
                    continue
        elif command == ">get":
            if not args:
                return
            _id = self.get_member_id_from_name(args[0])
            await message.channel.send(_id)
        elif command == ">ban":
            if not self.user_check(message) == 0:
                return
            if not args:
                return
            try:
                _id = int(args[0])
            except ValueError:
                _id = self.get_member_id_from_name(args[0])
            self.bans.append(_id)
            await message.channel.send("追加しました。")
        elif command == ">unban":
            if not self.user_check(message) == 0:
                return
            if not args:
                return
            try:
                _id = int(args[0])
            except ValueError:
                _id = self.get_member_id_from_name(args[0])
            if not _id in self.bans:
                await message.channel.send("いません")
                return
            await message.channel.send("削除しました。")
        elif command == ">banlist":
            if not self.user_check(message) == 0:
                return
            text = "```\n"
            for _id in self.bans:
                u = self.get_user(_id)
                text += f"{u.name}({u.id})\n"
            text += "```"
            await message.channel.send(text)
        elif command == ">help":
            embed = discord.Embed(title="Global Chat 3.0 for Discord", description="製作者: すみどら#8923", color=0x00ff00)
            embed.add_field(name=">tos", value="Terms of service(利用規約)をDMに送信します。", inline=False)
            embed.add_field(name=">get [ユーザー名]", value="名前からユーザーidを取得します。", inline=False)
            embed.add_field(name=">s [メッセージid]", value="global chatに送信されたメッセージを取得します。", inline=False)
            embed.add_field(name=">connect", value="コネクトします。チャンネル管理の権限が必要です。", inline=False)
            embed.add_field(name=">connect [カテゴリーネーム]",
                            value="指定したカテゴリーのチャンネルにコネクトします。チャンネル管理の権限が必要です。\nカテゴリーは追加次第お知らせします。", inline=False)
            embed.add_field(name=">disconnect", value="コネクト解除します。チャンネル管理の権限が必要です。", inline=False)
            embed.add_field(name=">adminhelp", value="for すみどら", inline=False)
            await message.channel.send(embed=embed)
        elif command == ">adminhelp":
            embed = discord.Embed(title="Global Chat 3.0 for Discord", description="製作者: すみどら#8923", color=0xff0000)
            embed.add_field(name=">ban [ユーザーネーム or id]", value="無期限banします。", inline=False)
            embed.add_field(name=">unban [ユーザーネーム or id]", value="banを解除します。", inline=False)
            embed.add_field(name=">banlist", value="banされているユーザーを表示します。", inline=False)
            await message.channel.send(embed=embed)

    def _do_cleanup(self):
        super()._do_cleanup()
        save_channel_webhook(self.webhooks)
        save_ban_members(self.bans)


client = MyClient()

client.run("NDM3OTE3NTI3Mjg5MzY0NTAw.XLrCIA.cuqcICWw8Ucvivk6ImHEkkjTZYc")
