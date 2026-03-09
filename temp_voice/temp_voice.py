import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TEMP_CHANNEL_PREFIX = "💠"
TEMP_CHANNEL_SUFFIX = "'s Room"
RESTRICTED_ROLE_ID = 682747720137834570


def _voice_channel_create_id():
    raw = os.getenv("VOICE_CHANNEL_CREATE_ID", "")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


class TempVoice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        create_channel_id = _voice_channel_create_id()
        if not create_channel_id:
            return

        if after.channel and after.channel.id == create_channel_id:
            new_channel_name = f"{TEMP_CHANNEL_PREFIX} {member.display_name} {TEMP_CHANNEL_SUFFIX}"

            guild = after.channel.guild
            category = after.channel.category
            create_temp_voice_channel = discord.utils.get(category.voice_channels, id=create_channel_id)

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=True),
            }
            restricted_role = guild.get_role(RESTRICTED_ROLE_ID)
            if restricted_role:
                overwrites[restricted_role] = discord.PermissionOverwrite(view_channel=False)

            new_channel = await guild.create_voice_channel(
                name=new_channel_name,
                category=category,
                overwrites=overwrites,
                reason="Creating a temporary voice channel",
            )

            if create_temp_voice_channel:
                await new_channel.edit(position=create_temp_voice_channel.position + 1)

            await member.move_to(new_channel)

        if before.channel and before.channel != after.channel:
            if before.channel.name.startswith(TEMP_CHANNEL_PREFIX) and len(before.channel.members) == 0:
                try:
                    await before.channel.delete()
                except Exception as e:
                    print(f"Error deleting the channel: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(TempVoice(bot))

