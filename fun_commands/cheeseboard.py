import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class CheeseBoard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.leaderboard_file = os.path.join(os.path.dirname(__file__), "cheese_leaderboard.json")
        
        # Vérifier si le fichier de leaderboard existe
        if not os.path.exists(self.leaderboard_file):
            # Créer le fichier et initialiser le leaderboard
            with open(self.leaderboard_file, 'w') as f:
                json.dump([], f)  # Initialiser le fichier avec une liste vide

    @app_commands.command(name='cheeseboard', description='Show the Certified Cheese Enjoyers leaderboard.')
    async def cheeseboard(self, interaction: discord.Interaction):
        # Charger le leaderboard
        with open(self.leaderboard_file, 'r') as f:
            leaderboard = json.load(f)

        if not leaderboard:
            await interaction.response.send_message("The leaderboard is empty.")
        else:
            # Créer un embed pour le leaderboard avec une couleur jaune
            embed = discord.Embed(
                title="🏆 Certified Cheese Enjoyers Leaderboard 🏆",
                color=discord.Color.from_rgb(255, 255, 102)  # Couleur jaune
            )

            # Ajouter des champs avec le classement et les noms avec l'emoji de fromage
            cheese_emoji = "🧀"  # Emoji de fromage
            for index, entry in enumerate(leaderboard, start=1):
                embed.add_field(name=f"**{index}. {entry['name']} {cheese_emoji}**", value="\u200b", inline=False)

            await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        role_id = 1296169417172062259  # ID du rôle "CERTIFIED CHEESE ENJOYER"
        
        if before.roles != after.roles:  # Vérifier si les rôles ont changé
            if discord.utils.get(after.roles, id=role_id):  # Si le membre a maintenant le rôle
                # Vérifier si le membre est déjà dans le leaderboard
                with open(self.leaderboard_file, 'r') as f:
                    leaderboard = json.load(f)

                # Ajouter le membre s'il n'est pas déjà dans le leaderboard
                if not any(entry['id'] == after.id for entry in leaderboard):
                    leaderboard.append({'id': after.id, 'name': after.name})
                    
                    # Sauvegarder le leaderboard mis à jour
                    with open(self.leaderboard_file, 'w') as f:
                        json.dump(leaderboard, f)

async def setup(bot: commands.Bot):
    await bot.add_cog(CheeseBoard(bot))
