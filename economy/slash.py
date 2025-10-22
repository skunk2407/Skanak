import discord
from discord import app_commands, Interaction
from discord.ext import commands

from economy.stats import load_stats  # ✅ on importe la fonction

OWNER_ID = 292381324390432778

MAX_LEN = 2000

class SlashEconomy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="write", description="Le bot écrit exactement ce que tu demandes.")
    @app_commands.describe(text="Le texte que le bot doit écrire (réservé à l'owner)")
    async def slash_write(self, interaction: Interaction, text: str):
        # Vérifie si c'est toi
        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message(
                "❌ Seul le propriétaire du serveur peut utiliser cette commande.",
                ephemeral=True  # visible uniquement par la personne
            )

        # Empêche les pings
        safe_mentions = discord.AllowedMentions(
            everyone=False, users=False, roles=False, replied_user=False
        )

        await interaction.response.send_message(text, allowed_mentions=safe_mentions)

    @app_commands.command(name="richest", description="Show the top 10 cheese holders.")
    async def slash_richest(self, interaction: Interaction):
        stats = load_stats()
        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message("This command must be used in a server.", ephemeral=True)

        entries = []
        for uid, data in stats.items():
            member = guild.get_member(int(uid))
            if member:
                entries.append((member, int(data.get('cheese', 0))))

        if not entries:
            return await interaction.response.send_message("No cheese data found on this server.", ephemeral=True)

        top10 = sorted(entries, key=lambda x: x[1], reverse=True)[:10]
        lines = [f"**{i}.** {m.mention} — {c:,} 🧀" for i, (m, c) in enumerate(top10, start=1)]

        embed = discord.Embed(
            title="🏆 Top 10 Cheese Holders",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(SlashEconomy(bot))
