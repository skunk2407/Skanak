import asyncio
import random

import discord
from discord.ext import commands, tasks

from .stats import get_user_stats, load_stats, save_stats

GENERAL_CHANNEL_ID = 577913608323727362


class SurpriseCog(commands.Cog):
    """Cog for periodic surprise cheese gifts."""

    def __init__(self, bot):
        self.bot = bot
        self.gift_task.start()

    def cog_unload(self):
        self.gift_task.stop()

    @tasks.loop(hours=10)
    async def gift_task(self):
        channel = self.bot.get_channel(GENERAL_CHANNEL_ID)
        if not channel:
            return

        cheese_amount = random.randint(400, 1000)
        message = await channel.send(
            f"🎁 A gift of **{cheese_amount}** 🧀 just spawned! React with 🎉 to claim it!"
        )
        await message.add_reaction("🎉")

        def check(reaction, user):
            return (
                user != self.bot.user
                and str(reaction.emoji) == "🎉"
                and reaction.message.id == message.id
            )

        try:
            _, user = await self.bot.wait_for("reaction_add", timeout=1200.0, check=check)
        except asyncio.TimeoutError:
            await channel.send("⏳ Time's up! No one grabbed the cheese.")
            await message.delete()
        else:
            stats = load_stats()
            entry = get_user_stats(stats, user.id)
            entry["cheese"] = entry.get("cheese", 0) + cheese_amount
            save_stats(stats)

            await channel.send(f"🎉 {user.mention} claimed **{cheese_amount}** 🧀!")
            await message.delete()

    @gift_task.before_loop
    async def before_gift_task(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(SurpriseCog(bot))

