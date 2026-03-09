import os

from discord.ext import commands

from storage.database import load_app_state, save_app_state

COUNTING_STATE_KEY = "counting.state"


def _counting_channel_id():
    raw = os.getenv("COUNTING_CHANNEL", "")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def load_count():
    data = load_app_state(COUNTING_STATE_KEY, default={"current_count": 0})
    if not isinstance(data, dict):
        data = {"current_count": 0}
    data.setdefault("current_count", 0)
    return data


def save_count(count_data):
    save_app_state(COUNTING_STATE_KEY, count_data)


class CountingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        channel_id = _counting_channel_id()
        if not channel_id:
            return
        if message.channel.id != channel_id:
            return

        count_data = load_count()
        current_count = int(count_data.get("current_count", 0))

        try:
            count_number = int(message.content.strip())
        except ValueError:
            await message.delete()
            return

        if count_number == current_count + 1:
            count_data["current_count"] = count_number
            save_count(count_data)
            await message.add_reaction("✅")
        else:
            await message.delete()


async def setup(bot):
    await bot.add_cog(CountingCog(bot))

