import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# On importe la migration, sans exécuter dès l'import
import migrate_stats

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members         = True
intents.reactions       = True
intents.message_content = True
intents.voice_states    = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        initial_extensions = [
            "application.application",
            "events.event",
            "welcome.welcome",
            "counting.counting",
            "fun_commands.commands",
            "fun_commands.cheeseboard",
            "fun_commands.help",
            "temp_voice.temp_voice",
            "meme_sender.meme_sender",
            "economy.economy",
            "economy.boutique",
            "economy.surprise",
            "economy.profile",
            "purge.purge_ban",
            "economy.slash",
            "economy.extras",
            "logs.mod_logs"
        ]
        for ext in initial_extensions:
            await self.load_extension(ext)

        # Sync des slash-commands
        await self.tree.sync()
        print(f"{self.user} — cogs loaded & slash commands synced.")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"{bot.user} est connecté et prêt !")

@bot.command()
async def sync(ctx):
    await bot.tree.sync()
    await ctx.send("Les slash-commands ont été synchronisées !")

# --- Migration des stats avant démarrage du bot ---
migrate_stats.migrate()

# --- Démarrage du bot (une seule fois) ---
bot.run(TOKEN)
