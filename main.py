import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

import migrate_stats
from storage.database import DATABASE_PATH, initialize_database, migrate_legacy_runtime_data

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN in environment.")

intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.message_content = True
intents.voice_states = True


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        initial_extensions = [
            "application.application",
            "application.suggestions",
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
            "economy.slash",
            "economy.extras",
            "logs.mod_logs",
        ]
        for ext in initial_extensions:
            await self.load_extension(ext)

        await self.tree.sync()
        print(f"{self.user} - cogs loaded & slash commands synced.")


bot = MyBot()


@bot.event
async def on_ready():
    print(f"{bot.user} est connecte et pret !")


@bot.command()
async def sync(ctx):
    await bot.tree.sync()
    await ctx.send("Les slash-commands ont ete synchronisees !")


initialize_database()
migrate_legacy_runtime_data()
migrate_stats.migrate()
print(f"[Storage] SQLite ready at: {DATABASE_PATH}")

bot.run(TOKEN)
