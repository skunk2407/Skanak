import discord
from discord.ext import commands

# List of role options for the dropdown menu
ROLE_OPTIONS = [
    discord.SelectOption(label="NSFW", value="711317052199141376", description="Access to NSFW channel 🔞"),
    discord.SelectOption(label="Spam Lover", value="845344682359783434", description="Access to spam channel 📳"),
    discord.SelectOption(label="Amogus", value="1240386965682130976", description="Ping for Among Us 🎮"),
    discord.SelectOption(label="Nuclear Nightmare", value="1333074885605331046", description="Ping for Nuclear Nightmare ☢️"),
    discord.SelectOption(label="R.E.P.O", value="1348009377768013846", description="Ping for playing REPO 😈"),
]

class RoleSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="Choose your roles...",
            min_values=0,  # Allows users to remove all roles
            max_values=len(ROLE_OPTIONS),  # Max selectable roles
            options=[discord.SelectOption(label=opt.label, value=opt.value, description=opt.description) for opt in ROLE_OPTIONS]
        )

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild

        if not guild:
            return await interaction.response.send_message("This command cannot be used in DMs.", ephemeral=True)

        # Fetch the role objects from the guild
        roles = {opt.value: discord.utils.get(guild.roles, id=int(opt.value)) for opt in ROLE_OPTIONS}

        # Get selected roles and remove unselected ones
        selected_roles = set(roles[val] for val in self.values if roles[val])
        all_role_values = set(roles[opt.value] for opt in ROLE_OPTIONS if roles[opt.value])

        await member.remove_roles(*all_role_values)  # Remove all related roles
        await member.add_roles(*selected_roles)  # Add only selected roles

        # Send confirmation message (only visible to the user)
        await interaction.response.send_message(
            f"🎭 **Roles updated!**\nAdded: {', '.join([r.name for r in selected_roles]) or 'None'}", ephemeral=True
        )

class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleSelect())

class SelfRole(commands.Cog):
    """Cog for self-assignable roles"""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def roles(self, ctx):
        """Sends the role selection menu"""
        embed = discord.Embed(title="🎭 Choose your roles!", description="Use the dropdown menu to select or remove roles.", color=discord.Color.green())
        await ctx.send(embed=embed, view=RoleView())

# Setup function for the cog
async def setup(bot):
    await bot.add_cog(SelfRole(bot))
