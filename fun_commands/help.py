from dataclasses import dataclass
from typing import Dict, List

import discord
from discord.ext import commands


@dataclass(frozen=True)
class HelpEntry:
    name: str
    usage: str
    description: str
    section: str
    examples: List[str]
    aliases: List[str]


MEMBER_HELP_ENTRIES: Dict[str, HelpEntry] = {
    "apply": HelpEntry(
        name="apply",
        usage="!apply",
        description="Start your community application form.",
        section="Getting Started",
        examples=["!apply"],
        aliases=[],
    ),
    "profile": HelpEntry(
        name="profile",
        usage="!profile [@member]",
        description="Show your economy profile card.",
        section="Profile",
        examples=["!profile", "!profile @Skunk"],
        aliases=[],
    ),
    "mybadges": HelpEntry(
        name="mybadges",
        usage="!mybadges [@member]",
        description="Browse unlocked badges with clean pagination.",
        section="Profile",
        examples=["!mybadges", "!mybadges @Skunk"],
        aliases=["profilebadges"],
    ),
    "badges": HelpEntry(
        name="badges",
        usage="!badges",
        description="See the badge guide and unlock conditions.",
        section="Profile",
        examples=["!badges"],
        aliases=[],
    ),
    "work": HelpEntry(
        name="work",
        usage="!work",
        description="Earn cheese from work (with cooldown).",
        section="Economy",
        examples=["!work"],
        aliases=[],
    ),
    "daily": HelpEntry(
        name="daily",
        usage="!daily",
        description="Claim your daily cheese and keep your streak.",
        section="Economy",
        examples=["!daily"],
        aliases=[],
    ),
    "share": HelpEntry(
        name="share",
        usage="!share @member <amount>",
        description="Share cheese with another member.",
        section="Economy",
        examples=["!share @Skunk 500"],
        aliases=[],
    ),
    "gamble": HelpEntry(
        name="gamble",
        usage="!gamble <amount>",
        description="50/50 gamble: win or lose your bet.",
        section="Economy",
        examples=["!gamble 200"],
        aliases=[],
    ),
    "steal": HelpEntry(
        name="steal",
        usage="!steal @member",
        description="Try to steal cheese from another member.",
        section="Economy",
        examples=["!steal @Skunk"],
        aliases=[],
    ),
    "blackjack": HelpEntry(
        name="blackjack",
        usage="!blackjack <amount>",
        description="Play blackjack against the dealer.",
        section="Economy",
        examples=["!blackjack 250", "!bj 250"],
        aliases=["bj"],
    ),
    "inventory": HelpEntry(
        name="inventory",
        usage="!inventory",
        description="Show your active boosts, shields and tokens.",
        section="Economy",
        examples=["!inventory"],
        aliases=[],
    ),
    "shop": HelpEntry(
        name="shop",
        usage="!shop",
        description="Open the shop and view all available items.",
        section="Shop",
        examples=["!shop"],
        aliases=[],
    ),
    "buy": HelpEntry(
        name="buy",
        usage="!buy <code or name>",
        description="Buy an item from the shop.",
        section="Shop",
        examples=["!buy #21", "!buy Double Work Ticket"],
        aliases=[],
    ),
    "lottery": HelpEntry(
        name="lottery",
        usage="!lottery",
        description="Show current lottery entries and estimated pot.",
        section="Shop",
        examples=["!lottery"],
        aliases=[],
    ),
    "rename": HelpEntry(
        name="rename",
        usage="!rename @member <new_nickname>",
        description="Use one rename token on a member for 24h.",
        section="Shop",
        examples=["!rename @Skunk CaptainSkunk"],
        aliases=[],
    ),
    "richest": HelpEntry(
        name="richest",
        usage="!richest",
        description="Show the top cheese balances in this server.",
        section="Community",
        examples=["!richest"],
        aliases=[],
    ),
    "cheese": HelpEntry(
        name="cheese",
        usage="!cheese",
        description="Try your luck for the Certified Cheese Enjoyer role.",
        section="Community",
        examples=["!cheese"],
        aliases=["fromage", "queso"],
    ),
    "birthday": HelpEntry(
        name="birthday",
        usage="!birthday",
        description="Open the birthday setup menu.",
        section="Community",
        examples=["!birthday"],
        aliases=[],
    ),
}

SECTION_ORDER = [
    "Getting Started",
    "Profile",
    "Economy",
    "Shop",
    "Community",
]

SECTION_EMOJIS = {
    "Getting Started": "🚀",
    "Profile": "🪪",
    "Economy": "🧀",
    "Shop": "🛍️",
    "Community": "🤝",
}


class MyHelp(commands.HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={"help": "Show the member-friendly command guide."})

    def _existing_member_entries(self) -> Dict[str, HelpEntry]:
        existing: Dict[str, HelpEntry] = {}
        bot = self.context.bot
        for name, entry in MEMBER_HELP_ENTRIES.items():
            if bot.get_command(name):
                existing[name] = entry
        return existing

    async def send_bot_help(self, mapping):
        entries = self._existing_member_entries()
        embed = discord.Embed(
            title="Skanak Member Help",
            description=(
                "Useful commands for members only.\n"
                "Use `!help <command>` to get details and examples."
            ),
            color=discord.Color.gold(),
        )

        for section in SECTION_ORDER:
            section_entries = [e for e in entries.values() if e.section == section]
            if not section_entries:
                continue
            section_entries.sort(key=lambda e: e.name)
            emoji = SECTION_EMOJIS.get(section, "•")
            lines = [f"`{e.usage}` — {e.description}" for e in section_entries]
            embed.add_field(
                name=f"{emoji} {section}",
                value="\n".join(lines),
                inline=False,
            )

        embed.add_field(
            name="Slash Commands",
            value=(
                "`/richest` — Top cheese balances"
            ),
            inline=False,
        )
        embed.set_footer(text="Hidden: owner/admin/moderation commands.")
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        entries = self._existing_member_entries()
        entry = entries.get(command.name)
        if not entry:
            # Try aliases in curated entries
            for candidate in entries.values():
                if command.name in candidate.aliases:
                    entry = candidate
                    break

        if not entry:
            embed = discord.Embed(
                title=f"!{command.name}",
                description="This command is not part of the member help guide.",
                color=discord.Color.red(),
            )
            return await self.get_destination().send(embed=embed)

        embed = discord.Embed(
            title=f"Command: !{entry.name}",
            description=entry.description,
            color=discord.Color.green(),
        )
        embed.add_field(name="Usage", value=f"`{entry.usage}`", inline=False)
        if entry.aliases:
            embed.add_field(name="Aliases", value=", ".join(f"`{a}`" for a in entry.aliases), inline=False)
        if entry.examples:
            embed.add_field(name="Examples", value="\n".join(f"`{x}`" for x in entry.examples), inline=False)
        embed.set_footer(text=f"Section: {entry.section}")
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        # Keep behavior simple and consistent with member-oriented help.
        await self.send_bot_help({})


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._original_help = bot.help_command
        bot.help_command = MyHelp()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._original_help


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
