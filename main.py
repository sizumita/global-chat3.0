"""
チャンネル保存はpickleで行く
"""
import asyncio
import pickle
import re
import sys

import aiohttp
import discord
from discord import Webhook

from manager import SQLManager
V = "3.0.3"
invite_compile = re.compile("(?:https?://)?discord(?:app\.com/invite|\.gg)/?[a-zA-Z0-9]+/?")
reply_compile = re.compile("^:>([0-9]{18}).+")
quote_compile = re.compile("^::>([0-9]{18}).+")
contract_e = discord.Embed(title="すみどらちゃん|Sigma 利用規約", description="すみどらちゃんは、Discordのさらなる発展を目指して作られたシステムです。\n"
                                                                   "このシステムでは、サーバーの規定は反映されず、\n下記の利用規約が適応されます。",
                           inline=False)
contract_e.add_field(name="本規約について", value='この利用規約（以下，「本規約」といいます。）は，すみどらちゃんコミュニティチーム（以下，「当チーム」といいます。）\n'
                                           'が提供するサービス"すみどらちゃん"(以下，「本サービス」といいます。）の利用条件を定めるものです。\n'
                                           '利用ユーザーの皆さま（以下，「ユーザー」といいます。）には，本規約に従い本サービスをご利用いただきます。', inline=False)
contract_e.add_field(name="第1条（適用）", value="本規約は，ユーザーと当チームとの間の本サービスの利用に関わる一切の関係に適用されるものとします。", inline=False)
contract_e.add_field(name="第2条（権限について）", value="""すみどらちゃん 開発者のすみどら#8923 (id:212513828641046529)は、
本サービスの全ての権限を保有します。""", inline=False)
contract_e.add_field(name="第3条（禁止事項）", value='''
ユーザーは，本サービスの利用にあたり，以下の行為をしてはなりません。
（1）法令または公序良俗に違反する行為
（2）犯罪行為に関連する行為
（3）当チームのサーバーまたはネットワークの機能を破壊したり，妨害したりする行為
（4）当チームのサービスの運営を妨害するおそれのある行為
（5）他のユーザーに関する個人情報等を収集または蓄積する行為
（6）他のユーザーに成りすます行為
（7）当チームのサービスに関連して，反社会的勢力に対して直接または間接に利益を供与する行為
（8）当チーム，本サービスの他の利用者または第三者の知的財産権，肖像権，プライバシー，名誉その他の権利または利益を侵害する行為
（9）過度に暴力的な表現，露骨な性的表現，人種，国籍，信条，性別，社会的身分，門地等による差別につながる表現，自殺，自傷行為，薬物乱用を誘引または助長する表現，その他反社会的な内容を含み他人に不快感を与える表現を，投稿または送信する行為
（10）他のお客様に対する嫌がらせや誹謗中傷を目的とする行為，その他本サービスが予定している利用目的と異なる目的で本サービスを利用する行為
（11）宗教活動または宗教団体への勧誘行為
（12）その他，当チームが不適切と判断する行為
（13) Discord利用規約に違反する行為
 (14) discordのinviteを投稿する行為
''', inline=False)
contract_e.add_field(name="第4条（global chatについて）", value='''
Global Chatでは、次のことをしてはいけません。
(1)r18発言をする行為(ただしnsfw指定が必要なカテゴリーは除きます。)
(2)r18,r18g画像を投稿する行為
(3)他人を煽る行為
(4)運営に対して反逆的な態度をとる行為
(5)その他、運営が不適切と判断した行為
''')
contract_e.add_field(name="第5条（利用制限および登録抹消）", value='''
当チームは以下の場合等には，事前の通知なく投稿データを削除し，ユーザーに対して本サービスの全部もしくは一部の利用を制限し、またはユーザーとしての登録を抹消することができるものとします。
（1）本規約のいずれかの条項に違反した場合
（2）当チームからの問い合わせその他の回答を求める連絡に対して7日間以上応答がない場合
（3）その他，当チームが本サービスの利用を適当でないと判断した場合
当チームは，当チームの運営行為によりユーザーに生じたいかなる損害についても、一切の責任を免責されるものとします。
また、ユーザー様同士のトラブルにつきましては、自己責任による当事者同士の解決を基本とし、当チームは一切の責任を免責されるものとします。
''')
contract_e.add_field(name="利用規約への同意について", value="本サービスを使用している時点で、利用規約に同意したこととなります。", inline=False)
contract_e.add_field(name="公式サーバー", value="https://discord.gg/fVsAjm9")
contract_e.add_field(name="BOT招待", value="https://discordapp.com/api/oauth2/"
                                         "authorize?client_id=437917527289364500&permissions=671410193&scope=bot")


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
        self.manager = SQLManager(self)
        self.channels = {}
        self.connecting = 0
        self.debug = []
        self.checking = []
        for key, value in self.webhooks.items():
            self.connecting += len(value.keys())
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

    async def set_pref(self):
        await self.change_presence(activity=discord.Game(name=f">help | {self.connecting} channels"))

    async def on_ready(self):
        await self.set_pref()
        await self.send_global_notice(text="すみどらちゃんが起動しました。", title="起動告知")

    def end(self):
        save_channel_webhook(self.webhooks)
        save_ban_members(self.bans)

    async def convert_message(self, message: discord.Message, embed: discord.Embed, content=""):
        """
        :param content:
        :param message:
        :param embed:
        :return: content, embed, settings
        """
        settings = {}
        if re.search(reply_compile, content):
            _id = re.search(reply_compile, content).groups()[0]
            m = await self.manager.get_message_from_id(int(_id))
            if not m:
                return content, embed, settings
            if not embed:
                embed = discord.Embed()
            settings['reply'] = m
            content = content.replace(f":>{_id}", "`Reply`")
            embed.add_field(name="replay from", value=f"{m.content}")
            embed.set_author(name=m.author.name, icon_url=m.author.avatar_url)
            embed.timestamp = m.created_at
        if re.search(quote_compile, content):
            _id = re.search(quote_compile, content).groups()[0]
            m = await self.manager.get_message_from_id(int(_id))
            if not m:
                return content, embed, settings
            if not embed:
                embed = discord.Embed()
            content = content.replace(f"::>{_id}", "`Quote`")
            embed.add_field(name="quote from", value=f"{m.content}")
            embed.set_author(name=m.author.name, icon_url=m.author.avatar_url)
            embed.timestamp = m.created_at
        return content, embed, settings

    async def send_global_message(self, message: discord.Message, name):
        channel = message.channel
        author = message.author
        content = message.clean_content
        settings = {}
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
        for key_, value in self.webhooks.items():
            for k, v in value.items():
                if k == channel.id:
                    cat = key_
                    break

        # ここから拡張機能処理
        if not content.startswith("*"):
            content, embed, settings = await self.convert_message(message, embed, content)
        else:
            content = content[1:]

        for _key, value in self.webhooks[cat].items():
            if message.channel.id == _key:
                continue

            async def send(webhook_url, _content, key):
                try:
                    async with aiohttp.ClientSession() as session:
                        webhook = Webhook.from_url(webhook_url, adapter=discord.AsyncWebhookAdapter(session))
                        if "reply" in settings.keys():
                            if int(key) == int(settings['reply'].channel.id):
                                _content = f"{settings['reply'].author.mention}\n" + _content
                            else:
                                _content = f"@{settings['reply'].author.name}" + _content

                        result = await webhook.send(
                            content=_content,
                            username=author.name,
                            avatar_url=author.avatar_url,
                            wait=True,
                            embed=embed,
                        )
                        message_id_list.append(result.id)
                        channel_id_list.append(key)
                except discord.errors.NotFound:
                    return

            self.loop.create_task(send(value, content, _key))
        await asyncio.sleep(2)
        await self.manager.save(message, channel_id_list, message_id_list, content)
        if message.guild.id in self.checking:
            self.loop.create_task(self.sending_check(message))

        for _key, value in self.webhooks[cat].items():
            ch = self.get_channel(_key)
            if not ch:
                continue
            if ch.guild.id in self.debug:
                embed = discord.Embed(title="DEBUG", description=content, timestamp=message.created_at)
                embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
                embed.set_footer(text=message.guild.name, icon_url=message.guild.icon_url)
                await ch.send(embed=embed)

    async def send_global_notice(self, name="global-chat", text="```\n```", title="お知らせ", mode="normal", **kwargs):
        if mode == "normal":
            embed = discord.Embed(title=title, description=text, color=0x00bfff)

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
                            await webhook.send(
                                username=self.user.name,
                                avatar_url=self.user.avatar_url,
                                embed=embed,

                            )
                    except discord.errors.NotFound:
                        return

                self.loop.create_task(send(webhook))
        return

    async def sending_check(self, message: discord.Message):
        await message.add_reaction("\U0001f44c")
        await asyncio.sleep(2)
        await message.remove_reaction("\U0001f44c", message.guild.me)

    def user_check(self, message):
        if message.author.id == 212513828641046529:
            return 0
        if message.guild.owner.id == message.author.id:
            return 1
        if message.author.guild_permissions.manage_channels:
            return 2
        return 3

    async def add_channel_global(self, channel: discord.TextChannel, guild: discord.Guild, name="global-chat"):
        try:
            webhooks = await channel.webhooks()
            if webhooks:
                webhook = webhooks[0]
            else:

                webhook = await channel.create_webhook(name='global-chat')
        except Exception:
            try:
                await channel.send(f"webhookの権限がありません！")
            except discord.Forbidden:
                pass
            return
        self.webhooks[name][channel.id] = webhook.url
        self.channels[channel.id] = name
        self.loop.create_task(self.send_global_notice(name, text=f"{guild.name} がコネクトしました。"))
        self.connecting += 1
        await self.set_pref()

    def get_member_id_from_name(self, names):
        for member in self.get_all_members():
            if member.name == " ".join(names):
                return int(member.id)

    async def on_message(self, message: discord.Message):
        if message.author.id == 212513828641046529:
            pass
        if message.author.id in self.bans:
            return
        if message.author.bot:
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
            if message.channel.id in self.channels.keys():
                return
            if not args:
                self.loop.create_task(self.add_channel_global(message.channel, message.guild, "global-chat"))

            else:
                if args[0] == "global-r18":
                    if not message.channel.is_nsfw():
                        await message.channel.send("NSFW指定をしてください。")
                        return
                    self.loop.create_task(self.add_channel_global(message.channel, message.guild, "global-r18"))
                elif args[0] in self.webhooks.keys():
                    self.loop.create_task(self.add_channel_global(message.channel, message.guild, args[0]))
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
            self.connecting -= 1
            await message.channel.send("接続解除しました。")

        elif command == ">s":
            try:
                channel_id, message_id = await self.manager.get_message_ids(int(args[0]))
                if not channel_id:
                    return
            except Exception:
                await message.channel.send("なし")
                return
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
            _id = self.get_member_id_from_name(args)
            messages = await self.manager.get_messages(_id)
            for m in messages:
                try:
                    await m.delete()
                except discord.Forbidden:
                    continue
        elif command == ">get":
            if not args:
                return
            _id = self.get_member_id_from_name(args)
            if not _id:
                await message.channel.send("なし")
                return
            await message.channel.send(_id)
        elif command == ">ban":
            if not self.user_check(message) == 0:
                return
            if not args:
                return
            try:
                _id = int(args[0])
            except ValueError:
                _id = self.get_member_id_from_name()
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
                _id = self.get_member_id_from_name(args)
            if not _id in self.bans:
                await message.channel.send("いません")
                return
            self.bans.remove(message.author.id)
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
        elif command == ">notice":
            desc = args[0]
            del args[0]
            await self.send_global_notice(text=desc, mode="update", name="更新情報", _list=args)

        elif command == ">debug":
            if not self.user_check(message) <= 2:
                return
            if message.guild.id in self.debug:
                self.debug.remove(message.guild.id)
                await message.channel.send("デバッグ機能をオフにしました。")
                return
            self.debug.append(message.guild.id)
            await message.channel.send("デバッグ機能をオンにしました。")

        elif command == ">checking":
            if not self.user_check(message) <= 2:
                return
            if message.guild.id in self.checking:
                await message.channel.send("送信チェック機能をオフにしました。")
                self.checking.remove(message.guild.id)
                return
            await message.channel.send("送信チェック機能をオンにしました。")
            self.checking.append(message.guild.id)
            return

        elif command == ">help":
            embed = discord.Embed(title=f"Global Chat {V} for Discord", description="製作者: すみどら#8923", color=0x00ff00)
            embed.add_field(name=">tos", value="Terms of service(利用規約)をDMに送信します。", inline=False)
            embed.add_field(name=">get [ユーザー名]", value="名前からユーザーidを取得します。", inline=False)
            embed.add_field(name=">s [メッセージid]", value="global chatに送信されたメッセージを取得します。", inline=False)
            embed.add_field(name=">connect", value="コネクトします。チャンネル管理の権限が必要です。", inline=False)
            embed.add_field(name=">connect [カテゴリーネーム]",
                            value="指定したカテゴリーのチャンネルにコネクトします。チャンネル管理の権限が必要です。\nカテゴリーは追加次第お知らせします。", inline=False)
            embed.add_field(name=">disconnect", value="コネクト解除します。チャンネル管理の権限が必要です。", inline=False)
            embed.add_field(name=">debug", value="デバッグ機能をオンにします。もう一度実行するとオフになります。チャンネル管理の権限が必要です。", inline=False)
            embed.add_field(name=">checking", value="送信チェック機能をオンにします。もう一度実行するとオフになります。チャンネル管理の権限が必要です。", inline=False)
            embed.add_field(name=">adminhelp", value="for すみどら", inline=False)
            await message.channel.send(embed=embed)
        elif command == ">adminhelp":
            embed = discord.Embed(title="Global Chat 3.0 for Discord", description="製作者: すみどら#8923", color=0xff0000)
            embed.add_field(name=">ban [ユーザーネーム or id]", value="無期限banします。", inline=False)
            embed.add_field(name=">unban [ユーザーネーム or id]", value="banを解除します。", inline=False)
            embed.add_field(name=">banlist", value="banされているユーザーを表示します。", inline=False)
            embed.add_field(name=">notice [description] <args>", value="おしらせします。", inline=False)
            await message.channel.send(embed=embed)
        elif command == ">tos":
            try:
                await message.author.send(embed=contract_e)
            except Exception:
                pass

        elif command == ">all":
            if not self.user_check(message) == 0:
                return
            for c in self.get_all_channels():
                if not isinstance(c, discord.TextChannel):
                    continue
                if c.name == "global-chat":
                    if c.id in self.channels.keys():
                        continue
                    await self.add_channel_global(c, c.guild, "global-chat")

    def _do_cleanup(self):
        super()._do_cleanup()
        save_channel_webhook(self.webhooks)
        save_ban_members(self.bans)


client = MyClient()
client.run(sys.argv[1])
