import asyncio
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, Modal, Select, TextInput, View

from storage.database import load_app_state, save_app_state

POTM_CHANNEL_ID = 1541552645121118279
TF_BOYS_ROLE_ID = 810161754775617553
POTM_WINNER_ROLE_ID = 1541558015239393331
POTM_STATE_KEY = "player_of_month.state.v1"
MAX_NOMINATIONS_PER_MEMBER = 2
MAX_FINALISTS = 5

CATEGORIES = {
    "scores": "High Scores and Killstreaks",
    "teamwork": "Teamwork and Discipline",
    "helping": "Helping or Training Other Players",
    "improvement": "Improvement or Memorable Actions",
}

MEMBERS_PER_PAGE = 25


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> dict:
    return {
        "version": 1,
        "phase": "idle",
        "test_mode": True,
        "label": "",
        "channel_id": POTM_CHANNEL_ID,
        "panel_message_id": 0,
        "result_message_id": 0,
        "nominations": [],
        "finalists": [],
        "votes": {},
        "winner_id": 0,
        "created_at": "",
        "updated_at": "",
    }


def _load_state() -> dict:
    state = load_app_state(POTM_STATE_KEY, default=_default_state())
    if not isinstance(state, dict):
        return _default_state()

    default = _default_state()
    for key, value in default.items():
        state.setdefault(key, value)
    if not isinstance(state.get("nominations"), list):
        state["nominations"] = []
    if not isinstance(state.get("finalists"), list):
        state["finalists"] = []
    if not isinstance(state.get("votes"), dict):
        state["votes"] = {}
    return state


def _save_state(state: dict) -> None:
    state["updated_at"] = _now_iso()
    save_app_state(POTM_STATE_KEY, state)


def _new_test_state(label: str) -> dict:
    state = _default_state()
    state.update(
        {
            "phase": "nominations",
            "test_mode": True,
            "label": label,
            "created_at": _now_iso(),
        }
    )
    return state


def _has_tf_boys_role(member: discord.Member) -> bool:
    return any(role.id == TF_BOYS_ROLE_ID for role in member.roles)


def _nomination_counts(state: dict) -> Counter:
    return Counter(
        int(item["nominee_id"])
        for item in state.get("nominations", [])
        if str(item.get("nominee_id", "")).isdigit()
    )


def _nominations_by_member(state: dict, member_id: int) -> list[dict]:
    return [
        item
        for item in state.get("nominations", [])
        if int(item.get("nominator_id", 0)) == member_id
    ]


def _rank_finalists(state: dict, eligible_ids: set[int]) -> list[int]:
    counts = _nomination_counts(state)
    ranked = sorted(
        (member_id for member_id in counts if member_id in eligible_ids),
        key=lambda member_id: (-counts[member_id], member_id),
    )
    return ranked[:MAX_FINALISTS]


def _build_nomination_panel(state: dict, disabled: bool = False) -> tuple[discord.Embed, View]:
    label = state.get("label") or "Test Cycle"
    embed = discord.Embed(
        title=f"🏆 TF Player of the Month — {label}",
        description=(
            "**TEST MODE — no monthly result is official yet.**\n\n"
            "Nominate a TF Boys member who distinguished themselves through "
            "their actions in **Holdfast**. Nominations and nominator identities "
            "remain private during this phase."
        ),
        color=discord.Color.gold(),
    )
    embed.add_field(
        name="Who can participate?",
        value=(
            f"Only members with the <@&{TF_BOYS_ROLE_ID}> role can nominate, "
            "be nominated, and vote."
        ),
        inline=False,
    )
    embed.add_field(
        name="What should nominations recognize?",
        value=(
            "🔥 High scores and killstreaks\n"
            "🤝 Teamwork and discipline\n"
            "🎓 Helping or training other players\n"
            "📈 Improvement or memorable actions"
        ),
        inline=False,
    )
    embed.add_field(
        name="Rules",
        value=(
            f"• Up to **{MAX_NOMINATIONS_PER_MEMBER} different players** per member\n"
            "• No self-nominations\n"
            "• A category and a genuine reason are required\n"
            "• Scores stay hidden until the final result"
        ),
        inline=False,
    )
    embed.set_footer(text="Use the button below to submit a private nomination.")

    view = View(timeout=None)
    view.add_item(
        Button(
            label="Nominate a TF Player",
            emoji="🏅",
            style=discord.ButtonStyle.primary,
            custom_id="potm:start_nomination",
            disabled=disabled,
        )
    )
    return embed, view


def _candidate_summary(state: dict, candidate_id: int) -> tuple[str, list[str]]:
    nominations = [
        item
        for item in state.get("nominations", [])
        if int(item.get("nominee_id", 0)) == candidate_id
    ]
    categories = Counter(str(item.get("category", "Other")) for item in nominations)
    category_text = ", ".join(name for name, _ in categories.most_common(2)) or "Holdfast contribution"
    reasons = [str(item.get("reason", "")).strip() for item in nominations]
    return category_text, [reason for reason in reasons if reason]


def _build_voting_panel(
    state: dict,
    guild: discord.Guild,
    disabled: bool = False,
) -> tuple[discord.Embed, View]:
    label = state.get("label") or "Test Cycle"
    embed = discord.Embed(
        title=f"🗳️ TF Player of the Month — {label}",
        description=(
            "**TEST MODE — final voting is now open.**\n\n"
            "The finalists below received the most valid nominations for their "
            "Holdfast contributions. Every eligible TF Boys member has one private vote."
        ),
        color=discord.Color.blurple(),
    )

    counts = _nomination_counts(state)
    for index, candidate_id in enumerate(state.get("finalists", []), start=1):
        member = guild.get_member(int(candidate_id))
        display = member.mention if member else f"<@{candidate_id}>"
        category_text, reasons = _candidate_summary(state, int(candidate_id))
        reason_preview = reasons[0][:350] if reasons else "Recognized by the TF Boys community."
        embed.add_field(
            name=f"{index}. {member.display_name if member else candidate_id}",
            value=(
                f"{display}\n"
                f"**Recognized for:** {category_text}\n"
                f"*“{reason_preview}”*\n"
                f"Nominations: **{counts[int(candidate_id)]}**"
            ),
            inline=False,
        )

    embed.add_field(
        name="Voting rules",
        value=(
            "• One vote per TF Boys member\n"
            "• You cannot vote for yourself\n"
            "• Your choice remains private\n"
            "• You may change your vote until voting closes"
        ),
        inline=False,
    )
    embed.set_footer(text="Use the button below to cast or change your vote.")

    view = View(timeout=None)
    view.add_item(
        Button(
            label="Cast or Change My Vote",
            emoji="🗳️",
            style=discord.ButtonStyle.success,
            custom_id="potm:start_vote",
            disabled=disabled,
        )
    )
    return embed, view


def _eligible_members(guild: discord.Guild) -> list[discord.Member]:
    return sorted(
        (
            member
            for member in guild.members
            if not member.bot and _has_tf_boys_role(member)
        ),
        key=lambda member: (member.display_name.casefold(), member.id),
    )


def _build_nominee_select(
    guild: discord.Guild,
    requested_page: int = 0,
) -> tuple[View, int, int, int]:
    eligible_members = _eligible_members(guild)
    total_members = len(eligible_members)
    total_pages = max(1, (total_members + MEMBERS_PER_PAGE - 1) // MEMBERS_PER_PAGE)
    page = max(0, min(requested_page, total_pages - 1))
    start = page * MEMBERS_PER_PAGE
    page_members = eligible_members[start : start + MEMBERS_PER_PAGE]

    view = View(timeout=180)
    options = [
        discord.SelectOption(
            label=member.display_name[:100],
            value=str(member.id),
            description=f"TF Boyz [HF] • {member}"[:100],
        )
        for member in page_members
    ]
    if options:
        view.add_item(
            Select(
                placeholder=f"Select a TF Boyz member — page {page + 1}/{total_pages}",
                options=options,
                min_values=1,
                max_values=1,
                custom_id="potm:nominee",
                row=0,
            )
        )
    view.add_item(
        Button(
            label="Previous",
            emoji="⬅️",
            style=discord.ButtonStyle.secondary,
            custom_id=f"potm:nominee_page:{page - 1}",
            disabled=page == 0,
            row=1,
        )
    )
    view.add_item(
        Button(
            label="Next",
            emoji="➡️",
            style=discord.ButtonStyle.secondary,
            custom_id=f"potm:nominee_page:{page + 1}",
            disabled=page >= total_pages - 1,
            row=1,
        )
    )
    return view, page, total_pages, total_members


def _build_category_select(nominee_id: int) -> View:
    view = View(timeout=180)
    options = [
        discord.SelectOption(label=label, value=key)
        for key, label in CATEGORIES.items()
    ]
    view.add_item(
        Select(
            placeholder="Choose the Holdfast contribution category",
            options=options,
            min_values=1,
            max_values=1,
            custom_id=f"potm:category:{nominee_id}",
        )
    )
    return view


def _build_vote_select(state: dict, guild: discord.Guild) -> View:
    view = View(timeout=180)
    options = []
    for candidate_id in state.get("finalists", []):
        member = guild.get_member(int(candidate_id))
        label = member.display_name if member else str(candidate_id)
        category_text, _ = _candidate_summary(state, int(candidate_id))
        options.append(
            discord.SelectOption(
                label=label[:100],
                value=str(candidate_id),
                description=category_text[:100],
            )
        )
    view.add_item(
        Select(
            placeholder="Select one finalist",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="potm:vote",
        )
    )
    return view


class NominationReasonModal(Modal, title="TF Player Nomination"):
    def __init__(
        self,
        cog: "PlayerOfMonthCog",
        nominee_id: int,
        category: str,
    ):
        super().__init__()
        self.cog = cog
        self.nominee_id = nominee_id
        self.category = category
        self.reason = TextInput(
            label="Why does this player deserve it?",
            placeholder="Describe what they did in Holdfast this month.",
            style=discord.TextStyle.paragraph,
            min_length=15,
            max_length=600,
            required=True,
        )
        self.evidence = TextInput(
            label="Screenshot or link (optional)",
            placeholder="Optional link supporting the nomination",
            max_length=300,
            required=False,
        )
        self.add_item(self.reason)
        self.add_item(self.evidence)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.submit_nomination(
            interaction,
            nominee_id=self.nominee_id,
            category=self.category,
            reason=str(self.reason.value).strip(),
            evidence=str(self.evidence.value).strip(),
        )


class PlayerOfMonthCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._lock = asyncio.Lock()
        self._ready_once = False

    async def _get_channel(self) -> Optional[discord.TextChannel]:
        channel = self.bot.get_channel(POTM_CHANNEL_ID)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(POTM_CHANNEL_ID)
            except discord.HTTPException:
                return None
        return channel if isinstance(channel, discord.TextChannel) else None

    async def _get_member(self, guild: discord.Guild, member_id: int) -> Optional[discord.Member]:
        member = guild.get_member(member_id)
        if member is not None:
            return member
        try:
            return await guild.fetch_member(member_id)
        except discord.HTTPException:
            return None

    async def _require_eligible(self, interaction: discord.Interaction) -> Optional[discord.Member]:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "This feature can only be used inside the TF Discord server.",
                ephemeral=True,
            )
            return None
        if interaction.user.bot or not _has_tf_boys_role(interaction.user):
            await interaction.response.send_message(
                "Only members with the **TF Boys** role can participate.",
                ephemeral=True,
            )
            return None
        return interaction.user

    async def _fetch_panel_message(self, state: dict) -> Optional[discord.Message]:
        message_id = int(state.get("panel_message_id", 0) or 0)
        if not message_id:
            return None
        channel = await self._get_channel()
        if channel is None:
            return None
        try:
            return await channel.fetch_message(message_id)
        except discord.HTTPException:
            return None

    async def _render_panel(self, state: dict, force_new: bool = False) -> Optional[discord.Message]:
        channel = await self._get_channel()
        if channel is None or channel.guild is None:
            return None

        phase = str(state.get("phase", "idle"))
        if phase == "nominations":
            embed, view = _build_nomination_panel(state)
        elif phase == "voting":
            embed, view = _build_voting_panel(state, channel.guild)
        else:
            return None

        message = None if force_new else await self._fetch_panel_message(state)
        if message is None:
            message = await channel.send(embed=embed, view=view)
            state["panel_message_id"] = message.id
            state["channel_id"] = channel.id
            _save_state(state)
        else:
            await message.edit(embed=embed, view=view)
        return message

    async def _disable_panel(self, state: dict, note: str) -> None:
        message = await self._fetch_panel_message(state)
        if message is None:
            return
        phase = str(state.get("phase", "idle"))
        if phase == "voting" and message.guild:
            embed, view = _build_voting_panel(state, message.guild, disabled=True)
        else:
            embed, view = _build_nomination_panel(state, disabled=True)
        embed.description = f"{embed.description}\n\n🔒 **{note}**"
        try:
            await message.edit(embed=embed, view=view)
        except discord.HTTPException:
            pass

    async def submit_nomination(
        self,
        interaction: discord.Interaction,
        nominee_id: int,
        category: str,
        reason: str,
        evidence: str,
    ) -> None:
        nominator = await self._require_eligible(interaction)
        if nominator is None or interaction.guild is None:
            return

        nominee = await self._get_member(interaction.guild, nominee_id)
        if nominee is None or nominee.bot or not _has_tf_boys_role(nominee):
            return await interaction.response.send_message(
                "That member is no longer eligible for this award.",
                ephemeral=True,
            )
        if nominee.id == nominator.id:
            return await interaction.response.send_message(
                "You cannot nominate yourself.",
                ephemeral=True,
            )

        async with self._lock:
            state = _load_state()
            if state.get("phase") != "nominations":
                return await interaction.response.send_message(
                    "The nomination phase is currently closed.",
                    ephemeral=True,
                )

            existing = _nominations_by_member(state, nominator.id)
            if len(existing) >= MAX_NOMINATIONS_PER_MEMBER:
                return await interaction.response.send_message(
                    f"You have already used both of your nominations for {state.get('label') or 'this cycle'}.",
                    ephemeral=True,
                )
            if any(int(item.get("nominee_id", 0)) == nominee.id for item in existing):
                return await interaction.response.send_message(
                    f"You have already nominated {nominee.mention} during this cycle.",
                    ephemeral=True,
                )

            state["nominations"].append(
                {
                    "nominator_id": nominator.id,
                    "nominee_id": nominee.id,
                    "category": category,
                    "reason": reason,
                    "evidence": evidence,
                    "created_at": _now_iso(),
                }
            )
            _save_state(state)
            remaining = MAX_NOMINATIONS_PER_MEMBER - len(existing) - 1

        await interaction.response.send_message(
            f"✅ Your private nomination for {nominee.mention} has been registered.\n"
            f"Category: **{category}**\n"
            f"Nominations remaining: **{remaining}**",
            ephemeral=True,
        )

    async def _handle_nominee_selection(self, interaction: discord.Interaction, nominee_id: int) -> None:
        nominator = await self._require_eligible(interaction)
        if nominator is None or interaction.guild is None:
            return

        state = _load_state()
        if state.get("phase") != "nominations":
            return await interaction.response.send_message(
                "The nomination phase is currently closed.",
                ephemeral=True,
            )

        nominee = await self._get_member(interaction.guild, nominee_id)
        if nominee is None or nominee.bot or not _has_tf_boys_role(nominee):
            return await interaction.response.send_message(
                "Please select a member who has the **TF Boys** role.",
                ephemeral=True,
            )
        if nominee.id == nominator.id:
            return await interaction.response.send_message(
                "You cannot nominate yourself.",
                ephemeral=True,
            )

        existing = _nominations_by_member(state, nominator.id)
        if len(existing) >= MAX_NOMINATIONS_PER_MEMBER:
            return await interaction.response.send_message(
                "You have already used both of your nominations.",
                ephemeral=True,
            )
        if any(int(item.get("nominee_id", 0)) == nominee.id for item in existing):
            return await interaction.response.send_message(
                f"You have already nominated {nominee.mention}.",
                ephemeral=True,
            )

        await interaction.response.edit_message(
            content=f"You selected {nominee.mention}. Now choose the Holdfast contribution category:",
            view=_build_category_select(nominee.id),
        )

    async def _handle_vote(self, interaction: discord.Interaction, candidate_id: int) -> None:
        voter = await self._require_eligible(interaction)
        if voter is None or interaction.guild is None:
            return

        async with self._lock:
            state = _load_state()
            if state.get("phase") != "voting":
                return await interaction.response.send_message(
                    "Final voting is currently closed.",
                    ephemeral=True,
                )
            finalists = {int(value) for value in state.get("finalists", [])}
            if candidate_id not in finalists:
                return await interaction.response.send_message(
                    "That player is not a finalist in the current cycle.",
                    ephemeral=True,
                )
            if candidate_id == voter.id:
                return await interaction.response.send_message(
                    "You cannot vote for yourself.",
                    ephemeral=True,
                )

            candidate = await self._get_member(interaction.guild, candidate_id)
            if candidate is None or candidate.bot or not _has_tf_boys_role(candidate):
                return await interaction.response.send_message(
                    "That finalist is no longer eligible.",
                    ephemeral=True,
                )

            previous = state["votes"].get(str(voter.id))
            state["votes"][str(voter.id)] = candidate_id
            _save_state(state)

        action = "changed" if previous else "recorded"
        await interaction.response.send_message(
            f"✅ Your private vote has been **{action}** for {candidate.mention}.",
            ephemeral=True,
        )

    async def _set_winner_role(self, guild: discord.Guild, winner: discord.Member) -> None:
        role = guild.get_role(POTM_WINNER_ROLE_ID)
        if role is None:
            raise RuntimeError("The TF Player of the Month role could not be found.")
        for member in list(role.members):
            if member.id != winner.id:
                await member.remove_roles(role, reason="New TF Player of the Month selected")
        if role not in winner.roles:
            await winner.add_roles(role, reason="TF Player of the Month winner")

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self._ready_once:
            return
        self._ready_once = True
        state = _load_state()
        if state.get("phase") in {"nominations", "voting"}:
            await self._render_panel(state)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.type != discord.InteractionType.component:
            return
        data = interaction.data or {}
        custom_id = data.get("custom_id")
        if not isinstance(custom_id, str) or not custom_id.startswith("potm:"):
            return

        if custom_id == "potm:start_nomination":
            member = await self._require_eligible(interaction)
            if member is None or interaction.guild is None:
                return
            state = _load_state()
            if state.get("phase") != "nominations":
                return await interaction.response.send_message(
                    "The nomination phase is currently closed.",
                    ephemeral=True,
                )
            used = len(_nominations_by_member(state, member.id))
            if used >= MAX_NOMINATIONS_PER_MEMBER:
                return await interaction.response.send_message(
                    "You have already used both of your nominations.",
                    ephemeral=True,
                )
            view, page, total_pages, total_members = _build_nominee_select(interaction.guild)
            if total_members == 0:
                return await interaction.response.send_message(
                    "No eligible TF Boyz members were found.",
                    ephemeral=True,
                )
            return await interaction.response.send_message(
                f"Select a TF Boyz member to nominate. You have **{MAX_NOMINATIONS_PER_MEMBER - used}** nomination(s) remaining.\n"
                f"Showing **page {page + 1}/{total_pages}** — {total_members} eligible members.",
                view=view,
                ephemeral=True,
            )

        if custom_id.startswith("potm:nominee_page:"):
            member = await self._require_eligible(interaction)
            if member is None or interaction.guild is None:
                return
            state = _load_state()
            if state.get("phase") != "nominations":
                return await interaction.response.send_message(
                    "The nomination phase is currently closed.",
                    ephemeral=True,
                )
            requested_page = custom_id.rsplit(":", 1)[-1]
            if not requested_page.lstrip("-").isdigit():
                return await interaction.response.send_message(
                    "Invalid member page.",
                    ephemeral=True,
                )
            view, page, total_pages, total_members = _build_nominee_select(
                interaction.guild,
                int(requested_page),
            )
            return await interaction.response.edit_message(
                content=(
                    f"Select a TF Boyz member to nominate.\n"
                    f"Showing **page {page + 1}/{total_pages}** — {total_members} eligible members."
                ),
                view=view,
            )

        if custom_id == "potm:nominee":
            values = data.get("values") or []
            if not values or not str(values[0]).isdigit():
                return await interaction.response.send_message("Invalid player selection.", ephemeral=True)
            return await self._handle_nominee_selection(interaction, int(values[0]))

        if custom_id.startswith("potm:category:"):
            parts = custom_id.split(":")
            values = data.get("values") or []
            if len(parts) != 3 or not parts[2].isdigit() or not values:
                return await interaction.response.send_message("Invalid category selection.", ephemeral=True)
            category = CATEGORIES.get(str(values[0]))
            if category is None:
                return await interaction.response.send_message("Invalid category selection.", ephemeral=True)
            member = await self._require_eligible(interaction)
            if member is None:
                return
            return await interaction.response.send_modal(
                NominationReasonModal(self, int(parts[2]), category)
            )

        if custom_id == "potm:start_vote":
            member = await self._require_eligible(interaction)
            if member is None or interaction.guild is None:
                return
            state = _load_state()
            if state.get("phase") != "voting":
                return await interaction.response.send_message(
                    "Final voting is currently closed.",
                    ephemeral=True,
                )
            return await interaction.response.send_message(
                "Select one finalist. Your choice is private and can be changed until voting closes.",
                view=_build_vote_select(state, interaction.guild),
                ephemeral=True,
            )

        if custom_id == "potm:vote":
            values = data.get("values") or []
            if not values or not str(values[0]).isdigit():
                return await interaction.response.send_message("Invalid finalist selection.", ephemeral=True)
            return await self._handle_vote(interaction, int(values[0]))

    @app_commands.command(
        name="potm-test-start",
        description="Start a fresh TF Player of the Month test nomination cycle.",
    )
    @app_commands.describe(label="Optional label displayed on the test panel")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test_start(self, interaction: discord.Interaction, label: Optional[str] = None) -> None:
        async with self._lock:
            current = _load_state()
            if current.get("phase") in {"nominations", "voting"}:
                return await interaction.response.send_message(
                    "A test cycle is already active. Use `/potm-test-reset` first if you want to replace it.",
                    ephemeral=True,
                )
            test_label = (label or datetime.now(timezone.utc).strftime("Test Cycle — %B %Y"))[:80]
            state = _new_test_state(test_label)
            _save_state(state)

        await interaction.response.defer(ephemeral=True)
        message = await self._render_panel(state, force_new=True)
        if message is None:
            return await interaction.followup.send(
                "The Player of the Month channel could not be found.",
                ephemeral=True,
            )
        await interaction.followup.send(
            f"✅ Test nominations are open: {message.jump_url}",
            ephemeral=True,
        )

    @app_commands.command(
        name="potm-test-final",
        description="Close test nominations and open the final vote.",
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test_final(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            return await interaction.response.send_message("Server only.", ephemeral=True)

        async with self._lock:
            state = _load_state()
            if state.get("phase") != "nominations":
                return await interaction.response.send_message(
                    "There is no open nomination phase to close.",
                    ephemeral=True,
                )
            eligible_ids = {
                member.id
                for member in interaction.guild.members
                if not member.bot and _has_tf_boys_role(member)
            }
            finalists = _rank_finalists(state, eligible_ids)
            if not finalists:
                return await interaction.response.send_message(
                    "At least one valid nomination is required before opening the final vote.",
                    ephemeral=True,
                )
            state["phase"] = "voting"
            state["finalists"] = finalists
            state["votes"] = {}
            _save_state(state)

        await interaction.response.defer(ephemeral=True)
        message = await self._render_panel(state)
        if message is None:
            return await interaction.followup.send("Could not update the voting panel.", ephemeral=True)
        await interaction.followup.send(
            f"✅ Final voting is open with **{len(finalists)}** finalist(s): {message.jump_url}",
            ephemeral=True,
        )

    @app_commands.command(
        name="potm-test-close",
        description="Close the test vote and announce the winner.",
    )
    @app_commands.describe(winner="Optional finalist used to resolve a tie or a no-vote test")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test_close(
        self,
        interaction: discord.Interaction,
        winner: Optional[discord.Member] = None,
    ) -> None:
        if interaction.guild is None:
            return await interaction.response.send_message("Server only.", ephemeral=True)

        async with self._lock:
            state = _load_state()
            if state.get("phase") != "voting":
                return await interaction.response.send_message(
                    "There is no open final vote to close.",
                    ephemeral=True,
                )
            finalists = {int(value) for value in state.get("finalists", [])}
            if winner is not None:
                if winner.id not in finalists:
                    return await interaction.response.send_message(
                        "The forced winner must be one of the current finalists.",
                        ephemeral=True,
                    )
                winner_id = winner.id
            else:
                vote_counts = Counter(int(value) for value in state.get("votes", {}).values())
                if not vote_counts:
                    return await interaction.response.send_message(
                        "No votes were cast. Select the optional `winner` argument to complete this test.",
                        ephemeral=True,
                    )
                highest = max(vote_counts.values())
                leaders = [member_id for member_id, count in vote_counts.items() if count == highest]
                if len(leaders) > 1:
                    nominations = _nomination_counts(state)
                    best_nomination_count = max(nominations[member_id] for member_id in leaders)
                    leaders = [
                        member_id
                        for member_id in leaders
                        if nominations[member_id] == best_nomination_count
                    ]
                if len(leaders) != 1:
                    return await interaction.response.send_message(
                        "The vote is tied. Run the command again and select a finalist with the optional `winner` argument.",
                        ephemeral=True,
                    )
                winner_id = leaders[0]

            winner_member = await self._get_member(interaction.guild, winner_id)
            if winner_member is None or winner_member.bot or not _has_tf_boys_role(winner_member):
                return await interaction.response.send_message(
                    "The selected winner is no longer eligible.",
                    ephemeral=True,
                )

            await interaction.response.defer(ephemeral=True)
            try:
                await self._set_winner_role(interaction.guild, winner_member)
            except (discord.Forbidden, discord.HTTPException, RuntimeError) as exception:
                return await interaction.followup.send(
                    f"Could not assign the winner role: {exception}",
                    ephemeral=True,
                )

            state["phase"] = "closed"
            state["winner_id"] = winner_id
            _save_state(state)

        await self._disable_panel({**state, "phase": "voting"}, "Voting is closed.")
        channel = await self._get_channel()
        if channel is None:
            return await interaction.followup.send("Winner selected, but the result channel is unavailable.", ephemeral=True)

        vote_counts = Counter(int(value) for value in state.get("votes", {}).values())
        nomination_counts = _nomination_counts(state)
        category_text, reasons = _candidate_summary(state, winner_id)
        result = discord.Embed(
            title=f"🏆 TF Player of the Month — {state.get('label') or 'Test Result'}",
            description=(
                f"Congratulations to {winner_member.mention}!\n\n"
                "This is a **test result** used to preview the complete Player of the Month flow."
            ),
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc),
        )
        result.set_thumbnail(url=winner_member.display_avatar.url)
        result.add_field(name="Recognized for", value=category_text, inline=False)
        result.add_field(name="Nominations", value=str(nomination_counts[winner_id]), inline=True)
        result.add_field(name="Final votes", value=str(vote_counts[winner_id]), inline=True)
        if reasons:
            result.add_field(name="Community recognition", value=f"*“{reasons[0][:700]}”*", inline=False)
        result.add_field(
            name="Reward",
            value=f"Awarded the <@&{POTM_WINNER_ROLE_ID}> role until the next winner is selected.",
            inline=False,
        )
        result.set_footer(text=f"Winner ID: {winner_id} • Test mode")
        result_message = await channel.send(embed=result)
        state["result_message_id"] = result_message.id
        _save_state(state)
        await interaction.followup.send(
            f"✅ Test completed and winner announced: {result_message.jump_url}",
            ephemeral=True,
        )

    @app_commands.command(
        name="potm-test-reset",
        description="Reset all Player of the Month test data and remove the test award role.",
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test_reset(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            return await interaction.response.send_message("Server only.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        async with self._lock:
            state = _load_state()
            await self._disable_panel(state, "This test cycle was reset by staff.")
            role = interaction.guild.get_role(POTM_WINNER_ROLE_ID)
            if role is not None:
                for member in list(role.members):
                    try:
                        await member.remove_roles(role, reason="Player of the Month test reset")
                    except discord.HTTPException:
                        pass
            _save_state(_default_state())
        await interaction.followup.send(
            "✅ Player of the Month test data was reset and the test winner role was removed.",
            ephemeral=True,
        )

    @app_commands.command(
        name="potm-test-status",
        description="Show the private status of the current Player of the Month test.",
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test_status(self, interaction: discord.Interaction) -> None:
        state = _load_state()
        counts = _nomination_counts(state)
        vote_counts = Counter(int(value) for value in state.get("votes", {}).values())
        details = [
            f"Phase: **{state.get('phase', 'idle')}**",
            f"Label: **{state.get('label') or 'None'}**",
            f"Nominations: **{len(state.get('nominations', []))}**",
            f"Unique nominees: **{len(counts)}**",
            f"Finalists: **{len(state.get('finalists', []))}**",
            f"Votes: **{len(state.get('votes', {}))}**",
        ]
        if counts:
            details.append("\nNomination totals:\n" + "\n".join(
                f"<@{member_id}> — {count}" for member_id, count in counts.most_common()
            ))
        if vote_counts:
            details.append("\nVote totals:\n" + "\n".join(
                f"<@{member_id}> — {count}" for member_id, count in vote_counts.most_common()
            ))
        await interaction.response.send_message("\n".join(details)[:1900], ephemeral=True)

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            message = "You need the **Manage Server** permission to use this test command."
        else:
            message = f"Player of the Month command failed: {error}"
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PlayerOfMonthCog(bot))
