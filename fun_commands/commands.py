import discord
from discord.ext import commands, tasks
import random
import json
import os
from datetime import datetime

from economy.badges import BADGES, award_badge

USER_STATS_PATH = '/home/container/Skanak/economy/user_stats.json'
CHEESE_ROLE_ID = 1296169417172062259  # CERTIFIED CHEESE ENJOYER role ID

# Default fields to initialize new users
DEFAULT_USER = {
    'cheese': 0,
    'last_work': None,
    'last_daily': None,
    'daily_streak': 0,
    'safe_mode_expiry': 0,
    'safe_mode_permanent': False,
    'next_work_multiplier': 1.0,
    'next_daily_multiplier': 1.0,
    'steal_boost': 0.0,
    'roles': [],
    'badges': []
}


def load_stats():
    try:
        with open(USER_STATS_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_stats(stats):
    with open(USER_STATS_PATH, 'w') as f:
        json.dump(stats, f, indent=4)

class FunCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # start daily cheese loop
        self.daily_cheese_task.start()
        # schedule initial badge scan after bot is ready
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
                uid = str(member.id)
                entry = stats.setdefault(uid, DEFAULT_USER.copy())
                entry.setdefault('badges', [])
                # Si le rôle est présent et que le badge n'est pas dans la liste, on l'ajoute
                if 'certified' not in entry['badges']:
                    entry['badges'].append('certified')
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
                uid = str(member.id)
                entry = stats.setdefault(uid, DEFAULT_USER.copy())
                entry['cheese'] = entry.get('cheese', 0) + 50
        save_stats(stats)

    @daily_cheese_task.before_loop
    async def before_daily(self):
        await self.bot.wait_until_ready()

    @commands.command(
        name="cheese",
        aliases=["fromage", "치즈", "奶酪", "käse", "juusto", "ost", "チーズ", "ser", "جبن", "keju", "पनीर", "queso"]
    )
    async def cheese(self, ctx):
        """Roll for the Certified Cheese Enjoyer role!"""
        drop_chance = random.randint(1, 1000)  # 0.1% chance
        stats = load_stats()
        uid = str(ctx.author.id)
        role = ctx.guild.get_role(CHEESE_ROLE_ID)

        if drop_chance == 1:
            if role and role not in ctx.author.roles:
                await ctx.author.add_roles(role)
                entry = stats.setdefault(uid, DEFAULT_USER.copy())
                if CHEESE_ROLE_ID not in entry['roles']:
                    entry['roles'].append(CHEESE_ROLE_ID)
                save_stats(stats)
                # Award certified badge
                if award_badge(ctx.author.id, 'certified'):
                    info = BADGES['certified']
                    embed = discord.Embed(
                        title="🎉 New Badge Unlocked!",
                        description=f"{ctx.author.mention}, you've just earned **{info['name']}**!",
                        color=discord.Color.gold()
                    )
                    embed.set_thumbnail(url=info['url'])
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
