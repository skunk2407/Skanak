import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class MyHelp(commands.HelpCommand):
    def __init__(self):
        super().__init__(
            command_attrs={'help': 'Shows this message or info about a specific command.'}
        )

    async def send_bot_help(self, mapping):
        embed = discord.Embed(
            title="🧀 TF Corporation Bot Help",
            description="Use `!help <command>` for prefix commands or `/help <slash>` for slash commands.",
            color=discord.Color.blue()
        )
        for cog, cmds in mapping.items():
            name = cog.qualified_name if cog else 'No Category'
            filtered = await self.filter_commands(cmds, sort=True)
            if filtered:
                lines = [f"`!{cmd.name}` — {cmd.short_doc or '—'}" for cmd in filtered]
                embed.add_field(name=name, value="\n".join(lines), inline=False)

        # Slash commands
        embed.add_field(
            name="Slash Commands",
            value="`/richest` — Show top 10 cheese holders on this server\n"
                  "`/write` — Make the bot send a message (admin only)",
            inline=False
        )
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(
            title=f"!{command.name}",
            description=command.help or 'No description',
            color=discord.Color.green()
        )
        embed.add_field(name="Usage", value=f"`{self.get_command_signature(command)}`", inline=False)
        if command.aliases:
            embed.add_field(name="Aliases", value=', '.join(command.aliases), inline=False)
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(
            title=f"Category: {cog.qualified_name}",
            description=cog.description or 'No description',
            color=discord.Color.purple()
        )
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        if filtered:
            lines = [f"`!{cmd.name}` — {cmd.short_doc or '—'}" for cmd in filtered]
            embed.add_field(name="Commands", value="\n".join(lines), inline=False)
        await self.get_destination().send(embed=embed)

class HelpCog(commands.Cog):
    """Cog to install custom help command"""
    def __init__(self, bot):
        self.bot = bot
        self._original_help = bot.help_command
        bot.help_command = MyHelp()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._original_help

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))