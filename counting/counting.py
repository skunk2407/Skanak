import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the counting channel ID from .env
COUNTING_CHANNEL_ID = int(os.getenv("COUNTING_CHANNEL"))

def load_count():
    file_path = os.path.join(os.path.dirname(__file__), 'count.json')
    # Vérifie si count.json existe
    if not os.path.exists(file_path):
        raise FileNotFoundError("Le fichier 'count.json' n'existe pas.")
    
    # Charge les données à partir de count.json
    with open(file_path, 'r') as f:
        count_data = json.load(f)  # Charge les données JSON en tant que dictionnaire
    return count_data

def save_count(count_data):
    file_path = os.path.join(os.path.dirname(__file__), 'count.json')
    with open(file_path, 'w') as f:
        json.dump(count_data, f)  # Sauvegarde les données en format JSON

class CountingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.count_file = 'count.json'

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return  # Ignore bot messages

        # Check if the message is in the correct counting channel
        if message.channel.id != COUNTING_CHANNEL_ID:
            return

        # Load the last count from the file
        count_data = load_count()
        current_count = count_data["current_count"]

        # Check if the message contains a number
        try:
            count_number = int(message.content)
        except ValueError:
            await message.delete()  # Supprime le message si ce n'est pas un nombre
            return

        # Check if the number is the next in sequence
        if count_number == current_count + 1:
            # Update the count and save
            count_data["current_count"] = count_number
            save_count(count_data)

            # Ajouter une réaction de validation
            await message.add_reaction("✅")
        else:
            # Supprime le message si le nombre n'est pas correct
            await message.delete()

# Fonction setup pour charger le cog
async def setup(bot):
    await bot.add_cog(CountingCog(bot))
