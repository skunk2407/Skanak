import asyncio
from datetime import datetime, timezone
from typing import Optional

import discord
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View

from storage.database import load_app_state, save_app_state

SUGGESTION_CHANNEL_ID = 1481234793470361692
SUGGESTION_META_KEY = "suggestions.meta"


def _default_meta() -> dict:
    return {
        "panel_channel_id": SUGGESTION_CHANNEL_ID,
        "panel_message_id": 0,
        "next_suggestion_id": 1,
    }


def _load_meta() -> dict:
    data = load_app_state(SUGGESTION_META_KEY, default=_default_meta())
    if not isinstance(data, dict):
        data = _default_meta()
    data.setdefault("panel_channel_id", SUGGESTION_CHANNEL_ID)
    data.setdefault("panel_message_id", 0)
    data.setdefault("next_suggestion_id", 1)
    return data


def _save_meta(meta: dict) -> None:
    save_app_state(SUGGESTION_META_KEY, meta)


def _build_panel_embed() -> discord.Embed:
    return discord.Embed(
        title="Submit Your Suggestion",
        description=(
            "Click a button below to submit a suggestion.\n\n"
            "Use **Submit Suggestion** to show your tag.\n"
            "Use **Submit Anonymous** to hide your identity."
        ),
        color=discord.Color.blurple(),
    )


def _build_panel_view() -> View:
    view = View(timeout=None)
    view.add_item(
        Button(
            label="Submit Suggestion",
            style=discord.ButtonStyle.primary,
            custom_id="suggest:start:public",
        )
    )
    view.add_item(
        Button(
            label="Submit Anonymous",
            style=discord.ButtonStyle.secondary,
            custom_id="suggest:start:anonymous",
        )
    )
    return view


class SuggestionModal(Modal, title="Submit Suggestion"):
    def __init__(self, cog: "SuggestionCog", anonymous: bool):
        super().__init__()
        self.cog = cog
        self.anonymous = anonymous

        self.suggestion_title = TextInput(
            label="Suggestion Title",
            placeholder="Short title for your suggestion",
            max_length=100,
            required=True,
        )
        self.suggestion_details = TextInput(
            label="Suggestion Details",
            placeholder="Describe your idea clearly and simply.",
            style=discord.TextStyle.paragraph,
            max_length=1500,
            required=True,
        )
        self.add_item(self.suggestion_title)
        self.add_item(self.suggestion_details)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.publish_suggestion(
            interaction=interaction,
            title=str(self.suggestion_title.value).strip(),
            details=str(self.suggestion_details.value).strip(),
            anonymous=self.anonymous,
        )


class SuggestionCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._lock = asyncio.Lock()

    async def _get_suggestion_channel(self) -> Optional[discord.TextChannel]:
        channel = self.bot.get_channel(SUGGESTION_CHANNEL_ID)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(SUGGESTION_CHANNEL_ID)
            except discord.HTTPException:
                channel = None
        if isinstance(channel, discord.TextChannel):
            return channel
        return None

    async def _reserve_suggestion_id(self) -> int:
        async with self._lock:
            meta = _load_meta()
            next_id = int(meta.get("next_suggestion_id", 1))
            if next_id < 1:
                next_id = 1
            meta["next_suggestion_id"] = next_id + 1
            _save_meta(meta)
            return next_id

    async def ensure_panel_message(self, force_new: bool = False) -> Optional[discord.Message]:
        channel = await self._get_suggestion_channel()
        if channel is None:
            return None

        meta = _load_meta()
        panel_message_id = int(meta.get("panel_message_id", 0) or 0)
        message = None

        if panel_message_id and not force_new:
            try:
                message = await channel.fetch_message(panel_message_id)
            except discord.HTTPException:
                message = None

        if message is None:
            message = await channel.send(embed=_build_panel_embed(), view=_build_panel_view())
            meta["panel_message_id"] = message.id
            meta["panel_channel_id"] = channel.id
            _save_meta(meta)
        else:
            try:
                await message.edit(embed=_build_panel_embed(), view=_build_panel_view())
            except discord.HTTPException:
                pass

        if not message.pinned:
            try:
                await message.pin(reason="Keep the suggestion panel always accessible.")
            except discord.HTTPException:
                pass

        return message

    async def publish_suggestion(
        self,
        interaction: discord.Interaction,
        title: str,
        details: str,
        anonymous: bool,
    ):
        if not interaction.guild:
            return await interaction.response.send_message(
                "Suggestions can only be submitted inside a server.",
                ephemeral=True,
            )

        channel = await self._get_suggestion_channel()
        if channel is None:
            return await interaction.response.send_message(
                "Suggestion channel is unavailable right now.",
                ephemeral=True,
            )

        suggestion_id = await self._reserve_suggestion_id()
        embed = discord.Embed(
            title=title,
            description=details,
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Suggestion #{suggestion_id}")

        if anonymous:
            embed.set_author(name="Anonymous Suggestion")
        else:
            embed.set_author(
                name=f"{interaction.user.display_name} Suggestion",
                icon_url=interaction.user.display_avatar.url,
            )
            embed.add_field(name="Author", value=interaction.user.mention, inline=False)

        suggestion_message = await channel.send(embed=embed)
        for emoji in ("\U0001F44D", "\U0001F44E", "\U0001F914"):
            try:
                await suggestion_message.add_reaction(emoji)
            except discord.HTTPException:
                pass

        await interaction.response.send_message(
            f"Suggestion posted in {channel.mention} as "
            f"{'anonymous' if anonymous else 'public'} (ID #{suggestion_id}).",
            ephemeral=True,
        )

    @commands.command(name="suggestpanel")
    @commands.has_permissions(manage_guild=True)
    async def suggestpanel(self, ctx: commands.Context):
        message = await self.ensure_panel_message(force_new=True)
        if message is None:
            return await ctx.send("Could not create the suggestion panel (channel not available).")
        await ctx.send(f"Suggestion panel ready in {message.channel.mention}: {message.jump_url}")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.ensure_panel_message(force_new=False)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        data = interaction.data or {}
        custom_id = data.get("custom_id")
        if not custom_id or not isinstance(custom_id, str):
            return

        if custom_id == "suggest:start:public":
            return await interaction.response.send_modal(SuggestionModal(self, anonymous=False))
        if custom_id == "suggest:start:anonymous":
            return await interaction.response.send_modal(SuggestionModal(self, anonymous=True))


async def setup(bot: commands.Bot):
    await bot.add_cog(SuggestionCog(bot))
