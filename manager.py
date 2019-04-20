"""
create table chat(
user_id int,
channel_id int,
message_id int,
id_list text
)
"""
import aiosqlite
import discord


class SQLManager:
    def __init__(self):
        self.db = "chat_data.db"

    async def save(self, message, channel_id_list, message_id_list, content):
        text = ""
        for channel_id, message_id in zip(channel_id_list, message_id_list):
            text += f"{channel_id}:{message_id},"
        async with aiosqlite.connect(self.db) as db:
            await db.execute('INSERT INTO chat VALUES(?,?,?,?,?)',
                             (message.author.id, message.channel.id, message.id, text, content))
            await db.commit()
        return True

    async def get_all_messages(self):
        _list = []
        async with aiosqlite.connect(self.db) as db:
            async with db.execute('SELECT * FROM chat') as cursor:
                async for row in cursor:
                    _list.append(row)
        list2 = []
        for x in _list:
            for y in x[3].split(","):
                if not y:
                    continue
                list2.append((x, y.split(":")))
        return list2

    async def get_message_ids(self, message_id):
        _list = await self.get_all_messages()
        channel_id = 0
        # [[channel_id,message_id],[channel_id,message_id]]
        result_message_id = 0
        result_channel_id = 0
        for a in _list:
            for b in a[1]:
                if int(b) == message_id:
                    channel_id = int(b[0])
                    result_channel_id = a[0][1]
                    result_message_id = a[0][2]
        if not channel_id:
            return False, False
        return result_channel_id, result_message_id

    async def get_messages(self, author_id, client: discord.Client):
        _list = await self.get_all_messages()
        channel_id_list = []
        message_id_list = []
        messages = []
        for x in _list:
            if not x[0][0] == author_id:
                continue
            channel_id_list.append(int(x[1][0]))
            message_id_list.append(int(x[1][1]))
        for channel_id, message_id in zip(channel_id_list, message_id_list):
            channel = client.get_channel(channel_id)
            try:
                m = await channel.fetch_message(message_id)
            except discord.NotFound:
                continue
            messages.append(m)
        return messages
