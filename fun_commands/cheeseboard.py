import discord
from discord.ext import commands
import json
import os

USER_STATS_PATH = '/home/container/Skanak/economy/user_stats.json'

class CheeseBoard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.leaderboard_file = os.path.join(os.path.dirname(__file__), "cheese_leaderboard.json")
        # Ensure leaderboard file exists
        if not os.path.exists(self.leaderboard_file):
            with open(self.leaderboard_file, 'w') as f:
                json.dump([], f)

    @commands.command(name='richest')
    async def richest(self, ctx: commands.Context):
        """Show top cheese holders on this server."""
        try:
            with open(USER_STATS_PATH, 'r') as f:
                stats = json.load(f)
        except FileNotFoundError:
            stats = {}

        entries = []
        for uid, data in stats.items():
            member = ctx.guild.get_member(int(uid)) if ctx.guild else None
            if member:
                cheese = data.get('cheese', 0)
                entries.append((member, cheese))

        if not entries:
            return await ctx.send("No cheese data found on this server.")

        # Sort and take top 10
        top = sorted(entries, key=lambda x: x[1], reverse=True)[:10]
        lines = [f"**{i}.** {member.mention} — {cheese} 🧀"
                 for i, (member, cheese) in enumerate(top, start=1)]

        embed = discord.Embed(
            title="🏆 Top 10 Cheese Tycoons",
            description="\n".join(lines),
            color=discord.Color.gold()
        )
        if ctx.guild and ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text="Based on total cheese balance")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        role_id = 1296169417172062259  # CERTIFIED CHEESE ENJOYER role
        had = any(r.id == role_id for r in before.roles)
        has = any(r.id == role_id for r in after.roles)
        if not had and has:
            with open(self.leaderboard_file, 'r') as f:
                leaderboard = json.load(f)
            if not any(e['id'] == after.id for e in leaderboard):
                leaderboard.append({'id': after.id, 'name': after.name})
                with open(self.leaderboard_file, 'w') as f:
                    json.dump(leaderboard, f, indent=4)

async def setup(bot: commands.Bot):
    await bot.add_cog(CheeseBoard(bot))
