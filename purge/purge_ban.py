import discord
from discord.ext import commands

OWNER_ID = 292381324390432778

class PurgeBan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='purge_ban')
    async def purge_ban(self, ctx, user_id: int):
        """Supprime TOUS les messages d’un utilisateur (banni ou non) dans TOUS les salons"""

        # 🔐 Vérif que c'est bien toi
        if ctx.author.id != OWNER_ID:
            await ctx.send("⛔ Tu n'as pas la permission d'utiliser cette commande.")
            return

        await ctx.send(f"🧹 Suppression des messages de l'utilisateur `{user_id}` en cours...")

        deleted = 0
        for channel in ctx.guild.text_channels:
            try:
                async for message in channel.history(limit=None, oldest_first=True):
                    if message.author.id == user_id:
                        try:
                            await message.delete()
                            deleted += 1
                        except Exception as e:
                            print(f"[Erreur suppression] #{channel.name} : {e}")
            except Exception as e:
                print(f"[Erreur lecture] #{channel.name} : {e}")

        embed = discord.Embed(
            title="✅ Purge terminée",
            description=f"Tous les messages de l'utilisateur avec l'ID `{user_id}` ont été supprimés avec succès.",
            color=discord.Color.green()
        )
        embed.add_field(name="Total supprimés", value=f"{deleted} messages", inline=False)
        embed.set_footer(text=f"Commande exécutée par {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

        await ctx.send(embed=embed)

    @commands.command(name='purge_word')
    async def purge_word(self, ctx, *, word: str):
        """Supprime tous les messages contenant un mot spécifique dans tous les salons"""
        
        # 🔐 Vérif que c'est bien toi
        if ctx.author.id != OWNER_ID:
            await ctx.send("⛔ Tu n'as pas la permission d'utiliser cette commande.")
            return

        word = word.lower()
        await ctx.send(f"🧹 Recherche et suppression des messages contenant `{word}`...")

        deleted = 0
        for channel in ctx.guild.text_channels:
            try:
                async for message in channel.history(limit=None, oldest_first=True):
                    if word in message.content.lower():
                        try:
                            await message.delete()
                            deleted += 1
                        except Exception as e:
                            print(f"[Erreur suppression] #{channel.name} : {e}")
            except Exception as e:
                print(f"[Erreur lecture] #{channel.name} : {e}")

        embed = discord.Embed(
            title="✅ Purge par mot-clé terminée",
            description=f"Tous les messages contenant `{word}` ont été supprimés.",
            color=discord.Color.red()
        )
        embed.add_field(name="Total supprimés", value=f"{deleted} messages", inline=False)
        embed.set_footer(text=f"Commande exécutée par {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PurgeBan(bot))
