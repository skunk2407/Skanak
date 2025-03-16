import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# Define the absolute path for the user stats JSON file
USER_STATS_PATH = '/home/container/Skanak/economy/user_stats.json'

# Define the roles and their prices
shop_items = {
    "VIP Color 1": {"id": 850716157303980052, "price": 10000},
    "VIP Color 2": {"id": 850714531227107338, "price": 10000},
    "VIP Color 3": {"id": 844598437683920946, "price": 10000},
    "VIP Color 4": {"id": 842912310468018186, "price": 10000},
    "💸 Wealthy Wacko [VIP]": {"id": 852474925914259476, "price": 100000},
    "Customized Color Role": {"id": 1309867587240329327, "price": 50000},
    "Customized Badge Role": {"id": 1309867842237235232, "price": 50000}
}

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

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='shop')
    async def shop(self, ctx):
        """Displays the shop with items and their prices."""
        embed = discord.Embed(title="TF Corporation Shop", color=int("DAF7A6", 16))  # Convert hex to int
        embed.add_field(
            name="Instructions",
            value="Use !buy <item name> to purchase an item.",
            inline=False
        )

        for item, info in shop_items.items():
            embed.add_field(
                name=item,
                value=f"Price: 🧀 {info['price']}\nItem ID: {info['id']}",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name='buy')
    async def buy(self, ctx, *, item_name_or_id: str):
        """Allows a user to buy an item from the shop."""
        user_id = str(ctx.author.id)
        stats = load_stats()

        if user_id not in stats:
            stats[user_id] = {"cheese": 0, "roles": []}  # Initialize user stats if they don't exist

        user_stats = stats[user_id]

        # Check if the item exists by name or ID
        item = None

        # Try to find the item by ID first
        try:
            item_id = int(item_name_or_id)  # Try parsing the item_name_or_id as an ID
            item = next((info for name, info in shop_items.items() if info['id'] == item_id), None)
        except ValueError:
            # If it's not an ID, fall back to searching by name
            item = next((info for name, info in shop_items.items() if name.lower() == item_name_or_id.lower()), None)

        if not item:
            await ctx.send("❌ This item does not exist in the shop!")
            return

        item_name = next(name for name, info in shop_items.items() if info == item)  # Get the item name
        item_info = item

        # Check if the user already owns the role
        if item_info['id'] in user_stats['roles']:
            await ctx.send("❌ You already own this role!")
            return

        # Check if the user has enough cheese
        if user_stats['cheese'] < item_info['price']:
            await ctx.send("❌ You do not have enough cheese to buy this item!")
            return

        # Deduct cheese and give the role
        user_stats['cheese'] -= item_info['price']
        user_stats['roles'].append(item_info['id'])
        save_stats(stats)

        role = discord.utils.get(ctx.guild.roles, id=item_info['id'])
        if role:
            await ctx.author.add_roles(role)  # Assign the role
            await ctx.send(f"🎉 You have purchased **{item_name}** for 🧀 {item_info['price']} cheese!")
        else:
            await ctx.send("❌ The role could not be found on this server!")

    @app_commands.command(name='richest', description='Show the leaderboard of users with the most cheese')
    async def richest(self, interaction: discord.Interaction):
        """Displays the leaderboard of users with the most cheese."""
        stats = load_stats()
        leaderboard = sorted(stats.items(), key=lambda x: x[1]['cheese'], reverse=True)[:10]

        if not leaderboard:
            await interaction.response.send_message("❌ No users have accumulated cheese yet.")
            return

        embed = discord.Embed(title="Richest Leaderboard", color=discord.Color.gold())
        for index, (user_id, user_data) in enumerate(leaderboard, start=1):
            user = await self.bot.fetch_user(int(user_id))
            embed.add_field(name=f"{index}. {user.name}", value=f"🧀 {user_data['cheese']} cheese", inline=False)

        await interaction.response.send_message(embed=embed)

    @commands.command(name='add')
    async def add_role(self, ctx, role_id: int):
        """Allows a user to add a role they have already purchased."""
        user_id = str(ctx.author.id)
        stats = load_stats()

        if user_id not in stats:
            stats[user_id] = {"cheese": 0, "roles": []}  # Initialize user stats if they don't exist

        user_stats = stats[user_id]

        # Check if the user has purchased the role
        if role_id not in user_stats['roles']:
            await ctx.send("❌ You need to buy this role first from the shop!")
            return

        # Add the role to the user
        role = discord.utils.get(ctx.guild.roles, id=role_id)
        if role:
            await ctx.author.add_roles(role)  # Assign the role
            await ctx.send(f"🎉 You have added the role {role.name}!")
        else:
            await ctx.send("❌ This role could not be found on the server.")

    @commands.command(name='remove')
    async def remove_role(self, ctx, role_id: int):
        """Allows a user to remove a role they have already purchased."""
        user_id = str(ctx.author.id)
        stats = load_stats()

        if user_id not in stats:
            stats[user_id] = {"cheese": 0, "roles": []}  # Initialize user stats if they don't exist

        user_stats = stats[user_id]

        # Check if the user has the role to remove
        if role_id not in user_stats['roles']:
            await ctx.send("❌ You do not have this role to remove!")
            return

        # Remove the role from the user
        role = discord.utils.get(ctx.guild.roles, id=role_id)
        if role:
            await ctx.author.remove_roles(role)  # Remove the role
            await ctx.send(f"🎉 You have removed the role {role.name}.")
        else:
            await ctx.send("❌ This role could not be found on the server.")

# Setup function to add the Cog
async def setup(bot):
    await bot.add_cog(Shop(bot))

