import discord
from discord import app_commands
from discord.ext import commands
import random

class FunCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Cheese command with multiple language aliases
    @commands.command(name="cheese", 
                      aliases=["fromage", "치즈", "奶酪", "käse", "juusto", "ost", "チーズ", "ser", "جبن","keju","पनीर","queso"])  
    async def cheese(self, ctx):
        cheese_responses = [
            "Who cut the cheese? 🧀",
            "Say CHEESE! 📸",
            "Did someone say cheese? 🧀",
            "Here's a cheesy joke: Why don't we talk to circles? They're pointless.",
            "https://cdn.discordapp.com/attachments/1216770917435183125/1296168464444297236/b9mnyc0mny7c1.png",
            "https://cdn.discordapp.com/attachments/1216770917435183125/1296168605481701469/whbtctep4oca1.png",
            "https://cdn.discordapp.com/attachments/1216770917435183125/1296168836919201833/ujg000yjwbba1.png",
            "https://youtu.be/jivajw4fnyQ",
            "https://tenor.com/view/cheese-gif-25332012",
            "Before you give the cheese, you must become the cheese.",
            "This is what happened when you don't give the cheese."
        ]

        drop_chance = random.randint(1, 1000)  # 1 in 1000 chance to get the role
        role = ctx.guild.get_role(1296169417172062259)  # Replace with your role ID

        if drop_chance == 1:
            if role not in ctx.author.roles:
                await ctx.author.add_roles(role)
                await ctx.send(f"🎉 Congratulations {ctx.author.mention}, you are now a **CERTIFIED CHEESE ENJOYER**! 🧀")
            else:
                await ctx.send(f"{ctx.author.mention}, you already have the **CERTIFIED CHEESE ENJOYER** role.")
        else:
            response = random.choice(cheese_responses)
            await ctx.send(response)

    # Slash command to make the bot write a message
    @app_commands.command(name="write", description="Make the bot send a message")
    @app_commands.describe(message="The message the bot should send")
    @app_commands.default_permissions(administrator=True)
    async def write(self, interaction: discord.Interaction, message: str):
        await interaction.channel.send(message)
        await interaction.response.send_message("Message sent!", ephemeral=True)

# Function to add the class as a cog
async def setup(bot):
    await bot.add_cog(FunCommands(bot))
