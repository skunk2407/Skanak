import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

VOICE_CHANNEL_CREATE_ID = int(os.getenv("VOICE_CHANNEL_CREATE_ID"))
TEMP_CHANNEL_PREFIX = "💠"
TEMP_CHANNEL_SUFFIX = "'s Room"
RESTRICTED_ROLE_ID = 682747720137834570  # Role ID to restrict

class TempVoice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Create temp channel when user joins the "Join to Create" channel
        if after.channel and after.channel.id == VOICE_CHANNEL_CREATE_ID:
            print(f"[TempVoice] {member.display_name} joined the target channel")

            guild = after.channel.guild
            category = after.channel.category  # can be None if channel is not in a category

            new_channel_name = f"{TEMP_CHANNEL_PREFIX} {member.display_name} {TEMP_CHANNEL_SUFFIX}"

            # Try to find the "➕ Join to Create" channel in the same category (if any)
            create_temp_voice_channel = None
            if category is not None:
                create_temp_voice_channel = discord.utils.get(
                    category.voice_channels,
                    name="➕ Join to Create"
                )

            # Build overwrites safely (never include None keys)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=True),
            }

            restricted_role = guild.get_role(RESTRICTED_ROLE_ID)
            if restricted_role is None:
                print(f"[TempVoice] ⚠️ Restricted role not found (ID={RESTRICTED_ROLE_ID}). Skipping overwrite.")
            else:
                overwrites[restricted_role] = discord.PermissionOverwrite(view_channel=False)

            # Create the new voice channel (catch errors so the bot doesn't "silently die")
            try:
                new_channel = await guild.create_voice_channel(
                    name=new_channel_name,
                    category=category,
                    overwrites=overwrites,
                    reason="Creating a temporary voice channel"
                )
            except Exception as e:
                print(f"[TempVoice] ❌ Error creating temp voice channel: {e}")
                return

            # Move the channel just below "➕ Join to Create" if found
            try:
                if create_temp_voice_channel:
                    await new_channel.edit(position=create_temp_voice_channel.position + 1)
            except Exception as e:
                print(f"[TempVoice] ⚠️ Error moving channel position: {e}")

            # Move member into the new channel
            try:
                await member.move_to(new_channel)
                print(f"[TempVoice] {member.display_name} was moved to {new_channel.name}")
            except Exception as e:
                print(f"[TempVoice] ⚠️ Error moving member: {e}")

        # Delete empty temp channels when people leave
        if before.channel and before.channel != after.channel:
            if before.channel.name.startswith(TEMP_CHANNEL_PREFIX) and len(before.channel.members) == 0:
                try:
                    await before.channel.delete()
                    print(f"[TempVoice] Temporary channel {before.channel.name} deleted (empty)")
                except Exception as e:
                    print(f"[TempVoice] Error deleting the channel: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(TempVoice(bot))
