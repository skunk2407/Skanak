import random

import discord
from discord.ext import commands, tasks

from economy.badges import BADGES, award_badge
from economy.stats import get_user_stats, load_stats, save_stats

CHEESE_ROLE_ID = 1296169417172062259  # CERTIFIED CHEESE ENJOYER role ID


class FunCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_cheese_task.start()
        bot.loop.create_task(self.initial_badge_scan())

    async def initial_badge_scan(self):
        await self.bot.wait_until_ready()
        stats = load_stats()
        updated = False
        for guild in self.bot.guilds:
            role = guild.get_role(CHEESE_ROLE_ID)
            if not role:
                continue
            for member in role.members:
                entry = get_user_stats(stats, member.id)
                entry.setdefault("badges", [])
                if "certified" not in entry["badges"]:
                    entry["badges"].append("certified")
                    updated = True
        if updated:
            save_stats(stats)

    def cog_unload(self):
        self.daily_cheese_task.cancel()

    @tasks.loop(hours=24)
    async def daily_cheese_task(self):
        """Credit 50 cheese to each Certified Cheese Enjoyer every 24h."""
        await self.bot.wait_until_ready()
        stats = load_stats()
        for guild in self.bot.guilds:
            role = guild.get_role(CHEESE_ROLE_ID)
            if not role:
                continue
            for member in role.members:
                entry = get_user_stats(stats, member.id)
                entry["cheese"] = entry.get("cheese", 0) + 50
        save_stats(stats)

    @daily_cheese_task.before_loop
    async def before_daily(self):
        await self.bot.wait_until_ready()

    @commands.command(
        name="cheese",
        aliases=["fromage", "치즈", "奶酪", "käse", "juusto", "ost", "チーズ", "ser", "جبن", "keju", "पनीर", "queso"],
    )
    async def cheese(self, ctx):
        """Roll for the Certified Cheese Enjoyer role!"""
        drop_chance = random.randint(1, 1000)  # 0.1% chance
        stats = load_stats()
        entry = get_user_stats(stats, ctx.author.id)
        role = ctx.guild.get_role(CHEESE_ROLE_ID)

        if drop_chance == 1:
            if role and role not in ctx.author.roles:
                await ctx.author.add_roles(role)
                if CHEESE_ROLE_ID not in entry["roles"]:
                    entry["roles"].append(CHEESE_ROLE_ID)
                save_stats(stats)

                if award_badge(ctx.author.id, "certified"):
                    info = BADGES["certified"]
                    embed = discord.Embed(
                        title="🎉 New Badge Unlocked!",
                        description=f"{ctx.author.mention}, you've just earned **{info['name']}**!",
                        color=discord.Color.gold(),
                    )
                    embed.set_thumbnail(url=info["url"])
                    await ctx.send(embed=embed)
                await ctx.send(
                    f"🎉 Congrats {ctx.author.mention}, you're now a **CERTIFIED CHEESE ENJOYER**!"
                    " You now earn 50 cheese per day automatically."
                )
            else:
                await ctx.send(f"{ctx.author.mention}, you already have the **CERTIFIED CHEESE ENJOYER** role.")
        else:
            cheese_responses = [
                "Who cut the cheese? 🧀",
                "Say CHEESE! 📸",
                "Did someone say cheese? 🧀",
                "Here's a cheesy joke: Why don't we talk to circles? They're pointless.",
                "Before you give the cheese, you must become the cheese.",
                "This is what happened when you don't give the cheese.",
            ]
            await ctx.send(random.choice(cheese_responses))


async def setup(bot):
    await bot.add_cog(FunCommands(bot))

