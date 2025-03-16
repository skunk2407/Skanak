import discord
from discord.ext import commands, tasks
import json
import random
import asyncio

# Define the absolute path for the user stats JSON file
USER_STATS_PATH = '/home/container/Skanak/economy/user_stats.json'

# Load user stats from JSON
def load_stats():
    try:
        with open(USER_STATS_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}  # Return an empty dict if the file doesn't exist

# Save user stats to JSON
def save_stats(stats):
    with open(USER_STATS_PATH, 'w') as f:
        json.dump(stats, f, indent=4)

# Define the channel ID for the general channel
GENERAL_CHANNEL_ID = 577913608323727362

class FunCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gift_task.start()

    def cog_unload(self):
        self.gift_task.stop()

    @tasks.loop(hours=10)  # Change the interval to 10 hours
    async def gift_task(self):
        channel = self.bot.get_channel(GENERAL_CHANNEL_ID)
        if channel is not None:
            cheese_amount = random.randint(400, 1000)  # Random amount of cheese
            message = await channel.send(f"🎁 **A gift of {cheese_amount} cheese is up for grabs!** 🎉 React with 🎉 to claim it!")

            # Add a reaction for users to click
            await message.add_reaction("🎉")

            def check(reaction, user):
                return user != self.bot.user and str(reaction.emoji) == "🎉" and reaction.message.id == message.id

            try:
                # Wait for the first reaction to the message with a timeout of 20 minutes
                reaction, user = await self.bot.wait_for('reaction_add', timeout=1200.0, check=check)  # 20 minutes
            except asyncio.TimeoutError:
                await channel.send("⏳ Time's up! No one claimed the cheese.")
                await message.delete()  # Delete the message after timeout
            else:
                user_id = str(user.id)
                stats = load_stats()

                if user_id not in stats:
                    stats[user_id] = {"cheese": 0, "roles": []}  # Initialize user stats if not present

                # Add the cheese to the user's stats
                stats[user_id]['cheese'] += cheese_amount
                save_stats(stats)

                # Send a message when the cheese is claimed
                await message.channel.send(f"🎉 {user.mention} claimed {cheese_amount} 🧀 🎊")

                # Delete the gift message after a user claims it
                await message.delete()  # Delete the message when claimed

    @gift_task.before_loop
    async def before_gift_task(self):
        await self.bot.wait_until_ready()  # Wait until the bot is ready

# Setup the cog
async def setup(bot):
    await bot.add_cog(FunCommands(bot))
