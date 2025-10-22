import discord
from discord.ext import commands, tasks
import os
import random

class MemeSender(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.send_meme.start()

    @tasks.loop(hours=3)
    async def send_meme(self):
        print("send_meme a été appelée.")

        meme_channel_id = int(os.getenv("MEME_CHANNEL_ID"))  # Récupère l'ID du salon "meme"
        meme_channel = self.bot.get_channel(meme_channel_id)

        # Vérifiez que le salon est valide
        if meme_channel is None:
            print(f"Le salon avec l'ID {meme_channel_id} n'a pas été trouvé.")
            return

        # Spécifiez le chemin du dossier temp
        temp_folder_path = os.path.join(os.path.dirname(__file__), 'temp')
        os.makedirs(temp_folder_path, exist_ok=True)  # Crée le dossier s'il n'existe pas

        # Récupérer les messages du salon "meme" (limité à 100 pour tester)
        messages = []
        async for message in meme_channel.history(limit=10000):
            messages.append(message)

        # Filtrer les messages qui contiennent des images ou des vidéos
        memes = []
        for message in messages:
            if message.author.bot:
                continue  # Ignore les messages de bots

            if message.attachments:
                print(f"Message de {message.author}: {len(message.attachments)} pièces jointes")
                for attachment in message.attachments:
                    if any(attachment.filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov']):
                        memes.append(attachment)

        print(f"Nombre de memes trouvés : {len(memes)}")  # Log pour le nombre de memes trouvés

        if memes:
            # Choisir un meme aléatoire
            meme_to_send = random.choice(memes)

            # Télécharger le fichier localement
            file_path = os.path.join(temp_folder_path, meme_to_send.filename)
            await meme_to_send.save(file_path)
            print(f"Téléchargé {meme_to_send.filename} dans {temp_folder_path}")

            # Envoyer le fichier dans le salon "meme"
            await meme_channel.send(file=discord.File(file_path))
            print(f"Envoyé le fichier {meme_to_send.filename} dans le salon {meme_channel.name}")

            # Supprimer le fichier localement après l'envoi
            os.remove(file_path)
            print(f"Supprimé le fichier {meme_to_send.filename} localement après envoi")
        else:
            print("Aucun meme trouvé dans le salon.")

    @send_meme.before_loop
    async def before_send_meme(self):
        await self.bot.wait_until_ready()  # Attend que le bot soit prêt

async def setup(bot):
    await bot.add_cog(MemeSender(bot))
