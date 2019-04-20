"""
チャンネル保存はpickleで行く

webhooks:
    channel id: webhook
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
        f.write(",".join(_list))


def load_ban_members():
    try:
        with open("ban.txt", "r") as f:
            return [int(i) for i in f.read().split(",")]
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
        self.limit_bans = load_ban_members()
        self.manager = SQLManager()
        self.channels = {}
        for key, value in self.webhooks.items():
            for k in list(value):
                self.channels[k] = key

    async def limit_ban(self, message, times, reason):
        self.limit_bans.append(message.author.id)
        await message.channel.send(f"{message.author.mention}, あなたは{reason}ため、制限時間付きbanを受けました。制限時間は{times}分です。")
        await asyncio.sleep(times * 60)
        self.limit_bans.remove(message.author.id)

    def end(self):
        save_channel_webhook(self.webhooks)

    async def send_global_message(self, message: discord.Message, name):
        channel = message.channel
        author = message.author
        content = message.clean_content
        message_id_list = [message.id]
        channel_id_list = [message.channel.id]
        if re.search(invite_compile, message.content):
            self.loop.create_task(self.limit_ban(message, 60, "招待を送信した"))
            return
        if message.mention_everyone:
            self.loop.create_task(self.limit_ban(message, 60, "everyoneメンションを送信した"))
            return

        cat = ""
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
                            wait=True
                        )
                        message_id_list.append(result.id)
                        channel_id_list.append(key)
                except discord.errors.NotFound:
                    return
            self.loop.create_task(send(value))
        await asyncio.sleep(2)
        await self.manager.save(message, channel_id_list, message_id_list)

    async def send_global_notice(self, text, title="", mode="normal", **kwargs):
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
        if message.author.id in self.limit_bans:
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
        self.loop.create_task(self.send_global_notice(f"{message.guild.name} がコネクトしました。"))

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
            if not args:
                return
            try:
                _id = int(args[0])
            except ValueError:
                _id = self.get_member_id_from_name(args[0])
            self.limit_bans.append(_id)
            await message.channel.send("追加しました。")

    def _do_cleanup(self):
        super()._do_cleanup()
        save_channel_webhook(self.webhooks)
        save_ban_members(self.limit_bans)


client = MyClient()

client.run("NDM3OTE3NTI3Mjg5MzY0NTAw.XLrCIA.cuqcICWw8Ucvivk6ImHEkkjTZYc")