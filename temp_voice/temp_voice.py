import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

# Fetch the channel ID and other configurations from the .env file
VOICE_CHANNEL_CREATE_ID = int(os.getenv("VOICE_CHANNEL_CREATE_ID"))
TEMP_CHANNEL_PREFIX = "💠"
TEMP_CHANNEL_SUFFIX = "'s Room"
RESTRICTED_ROLE_ID = 682747720137834570  # Role ID to restrict

class TempVoice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if after.channel and after.channel.id == VOICE_CHANNEL_CREATE_ID:
            print(f"{member.display_name} joined the target channel")

            new_channel_name = f"{TEMP_CHANNEL_PREFIX} {member.display_name} {TEMP_CHANNEL_SUFFIX}"

            guild = after.channel.guild
            category = after.channel.category

            # Rechercher le canal "➕ Join to Create"
            create_temp_voice_channel = discord.utils.get(category.voice_channels, name="➕ Join to Create")

            # Définir les permissions pour le nouveau canal
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=True),  # Autoriser tous à voir
                guild.get_role(RESTRICTED_ROLE_ID): discord.PermissionOverwrite(view_channel=False),  # Restreindre le rôle spécifique
            }

            # Créer le nouveau canal vocal sans définir la position
            new_channel = await guild.create_voice_channel(
                name=new_channel_name,
                category=category,
                overwrites=overwrites,
                reason="Creating a temporary voice channel"
            )

            # Déplacer le nouveau canal juste en dessous du canal "➕ Join to Create"
            if create_temp_voice_channel:
                await new_channel.edit(position=create_temp_voice_channel.position + 1)

            await member.move_to(new_channel)
            print(f"{member.display_name} was moved to {new_channel.name}")

        if before.channel and before.channel != after.channel:
            if before.channel.name.startswith(TEMP_CHANNEL_PREFIX) and len(before.channel.members) == 0:
                try:
                    await before.channel.delete()
                    print(f"Temporary channel {before.channel.name} was deleted because it is empty")
                except Exception as e:
                    print(f"Error deleting the channel: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(TempVoice(bot))

