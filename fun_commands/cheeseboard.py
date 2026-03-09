import discord
from discord.ext import commands

from economy.stats import load_stats
from storage.database import load_app_state, save_app_state

CHEESE_ROLE_ID = 1296169417172062259
CHEESE_LEADERBOARD_KEY = "fun.cheese_leaderboard"


class CheeseBoard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="richest")
    async def richest(self, ctx: commands.Context):
        """Show top cheese holders on this server."""
        stats = load_stats()

        entries = []
        for uid, data in stats.items():
            member = ctx.guild.get_member(int(uid)) if ctx.guild else None
            if member:
                cheese = int(data.get("cheese", 0))
                entries.append((member, cheese))

        if not entries:
            return await ctx.send("No cheese data found on this server.")

        top = sorted(entries, key=lambda x: x[1], reverse=True)[:10]
        lines = [f"**{i}.** {member.mention} — {cheese} 🧀" for i, (member, cheese) in enumerate(top, start=1)]

        embed = discord.Embed(
            title="🏆 Top 10 Cheese Tycoons",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        if ctx.guild and ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text="Based on total cheese balance")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        had = any(r.id == CHEESE_ROLE_ID for r in before.roles)
        has = any(r.id == CHEESE_ROLE_ID for r in after.roles)
        if not had and has:
            leaderboard = load_app_state(CHEESE_LEADERBOARD_KEY, default=[])
            if not isinstance(leaderboard, list):
                leaderboard = []
            if not any(e.get("id") == after.id for e in leaderboard if isinstance(e, dict)):
                leaderboard.append({"id": after.id, "name": after.name})
                save_app_state(CHEESE_LEADERBOARD_KEY, leaderboard)


async def setup(bot: commands.Bot):
    await bot.add_cog(CheeseBoard(bot))

