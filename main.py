import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

intents = discord.Intents.default()
intents.members = True  # Activez l'intent des membres
intents.message_content = True  # Nécessaire pour les slash commands dans certains cas
intents.voice_states = True  # Active les updates des salons vocaux
bot = commands.Bot(command_prefix="!", intents=intents)

# Charger le fichier .env pour récupérer le token
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Charger les extensions (cogs)
async def setup_extensions():
    #await bot.load_extension("birthday.birthday")
    await bot.load_extension("welcome.welcome")
    await bot.load_extension("counting.counting")
    await bot.load_extension("fun_commands.commands")
    await bot.load_extension("fun_commands.cheeseboard")
    await bot.load_extension("fun_commands.roles")
    await bot.load_extension("temp_voice.temp_voice")
    await bot.load_extension("meme_sender.meme_sender")
    await bot.load_extension("economy.economy")
    await bot.load_extension("economy.boutique")
    await bot.load_extension("economy.surprise")

@bot.event
async def on_ready():
    await setup_extensions()
    await bot.tree.sync()  # Synchroniser les commandes après le chargement des cogs
    print(f"{bot.user} est connecté !")

    # Option : Vérifier les anniversaires immédiatement au démarrage
    birthday_cog = bot.get_cog("BirthdayCog")
    if birthday_cog:
        print("Vérification immédiate des anniversaires au démarrage...")
        await birthday_cog.check_birthdays()

@bot.command()
async def sync(ctx):
    await bot.tree.sync()
    await ctx.send("Les commandes slash ont été synchronisées.")

bot.run(TOKEN)
