import discord
import os
import random
from discord.ext import commands

class WelcomeCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = member.guild.system_channel  # Change this if needed
        if channel is None:
            print("ERROR: No system channel defined.")
            return

        # IDs des channels à mentionner
        verification_channel_id = 1003591867151163453
        rules_channel_id = 591048531058491402
        role_id = 682747720137834570  # Role ID to assign 682747720137834570

        # Assign role automatically
        role = member.guild.get_role(role_id)
        if role:
            await member.add_roles(role)
        else:
            print(f"ERROR: Role with ID {role_id} not found.")

        embed = discord.Embed(
            title=f"Welcome to {member.guild.name}!",
            description=(
                "\n\n"
                "**⊱ ───── {☠️ ⋅ ✦ ⋅ ☠️} ───── ⊰**\n"
                f"🟢 Go to <#{verification_channel_id}> and explain why you joined!\n"
                f"🟢 Check <#{rules_channel_id}> to accept the rules!\n"
                "🟢 Have fun and stay out of trouble!\n"
                "**⊱ ───── {☠️ ⋅ ✦ ⋅ ☠️} ───── ⊰**\n\n"
                f"👥 We now have **{member.guild.member_count}** members!"
            ),
            color=discord.Color.green()
        )

        # Add server icon if available
        if member.guild.icon:
            embed.set_thumbnail(url=member.guild.icon.url)

        embed.set_footer(text=f"User: {member.name} • {member.joined_at.strftime('%d/%m/%Y %H:%M')}")

        # Select a random background
        background_folder = "/home/container/Skanak/welcome/"
        backgrounds = [f for f in os.listdir(background_folder) if f.startswith("background") and f.endswith(".jpg")]

        if backgrounds:
            selected_background = random.choice(backgrounds)
            background_path = os.path.join(background_folder, selected_background)

            try:
                with open(background_path, "rb") as f:
                    file = discord.File(f, filename=selected_background)
                    embed.set_image(url=f"attachment://{selected_background}")
                    await channel.send(f"Welcome {member.mention}!", file=file, embed=embed)
            except FileNotFoundError:
                print(f"ERROR: The image {background_path} was not found.")
                await channel.send(f"Welcome {member.mention}! 🎉", embed=embed)
        else:
            print("ERROR: No background images found.")
            await channel.send(f"Welcome {member.mention}! 🎉", embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        channel = member.guild.system_channel  # Change this if needed
        if channel is None:
            return

        farewell_messages = [
            f"{member.name} just left... Was it something we said? 😢",
            f"Another one bites the dust! Goodbye, {member.name}! 👋",
            f"{member.name} has left the server. They’ll be missed... by someone, probably. 🤔",
            f"Poof! {member.name} disappeared like a magician. 🎩✨",
            f"{member.name} escaped the Matrix. Will they return? 🕶️"
        ]

        await channel.send(random.choice(farewell_messages))

async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCommand(bot))