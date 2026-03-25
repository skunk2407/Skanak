import time
from datetime import datetime, timedelta, timezone
from typing import Dict

import discord
from discord.ext import commands, tasks
from discord.ui import Button, Modal, TextInput, View

from storage.database import load_app_state, save_app_state

APPLICATION_STATE_KEY = "application.votes"
HOLDFAST_CHANNEL_ID = 1106197912075116614
VOTE_DURATION_HOURS = 12
MIN_TOTAL_VOTES = 5


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ts() -> int:
    return int(_now_utc().timestamp())


def _fmt_deadline(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _new_application_id(user_id: int) -> str:
    return f"{user_id}-{int(time.time())}"


def _load_applications() -> Dict[str, dict]:
    data = load_app_state(APPLICATION_STATE_KEY, default={})
    return data if isinstance(data, dict) else {}


def _save_applications(data: Dict[str, dict]) -> None:
    save_app_state(APPLICATION_STATE_KEY, data)


def _build_start_view() -> View:
    view = View(timeout=None)
    view.add_item(
        Button(
            label="Start Application",
            style=discord.ButtonStyle.primary,
            custom_id="apply:start",
        )
    )
    return view


def _build_vote_view(app_id: str, disabled: bool = False) -> View:
    view = View(timeout=None)
    approve = Button(
        label="Approve",
        style=discord.ButtonStyle.success,
        custom_id=f"apply:vote:{app_id}:approve",
        disabled=disabled,
    )
    reject = Button(
        label="Reject",
        style=discord.ButtonStyle.danger,
        custom_id=f"apply:vote:{app_id}:reject",
        disabled=disabled,
    )
    view.add_item(approve)
    view.add_item(reject)
    return view


class ApplicationModal(Modal, title="Community Application"):
    def __init__(self, cog: "ApplyCog"):
        super().__init__()
        self.cog = cog
        self.reason = TextInput(
            label="Why do you want to join?",
            placeholder="Tell us in 1-3 short sentences.",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True,
        )
        self.ingame_name = TextInput(
            label="What is your in-game name?",
            placeholder="Your exact in-game name",
            max_length=60,
            required=True,
        )
        self.setup = TextInput(
            label="Are you a console player? Do you use any soundboard?",
            placeholder="Explain your setup in your own words.",
            max_length=100,
            required=True,
        )
        self.gameplay = TextInput(
            label="What is your favorite class and your average kills per round?",
            placeholder="Tell us about your playstyle.",
            max_length=150,
            required=True,
        )
        self.background = TextInput(
            label="How many hours do you have? What was your old regiment if you had one? Do you play regularly?",
            placeholder="Share anything useful about your playtime and background.",
            style=discord.TextStyle.paragraph,
            max_length=300,
            required=True,
        )
        self.add_item(self.reason)
        self.add_item(self.ingame_name)
        self.add_item(self.setup)
        self.add_item(self.gameplay)
        self.add_item(self.background)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        answers = {
            "Why do you want to join?": str(self.reason.value).strip(),
            "In-game name": str(self.ingame_name.value).strip(),
            "Are you a console player? Do you use any soundboard?": str(self.setup.value).strip(),
            "Favorite class and average kills per round": str(self.gameplay.value).strip(),
            "Hours played, old regiment if any, and regular activity": str(self.background.value).strip(),
        }
        await self.cog.submit_application(interaction, answers)


class ApplyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.review_pending.start()

    def cog_unload(self) -> None:
        self.review_pending.cancel()

    @commands.command(name="apply")
    async def apply(self, ctx: commands.Context) -> None:
        embed = discord.Embed(
            title="Apply to Join",
            description=(
                "Click **Start Application** and fill the form.\n\n"
                "1. Click the button\n"
                "2. Fill each field\n"
                "3. Submit the modal\n\n"
                "Your application will then be posted in the community voting channel."
            ),
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=embed, view=_build_start_view())

    async def submit_application(self, interaction: discord.Interaction, answers: Dict[str, str]) -> None:
        if not interaction.guild:
            return await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )

        channel = self.bot.get_channel(HOLDFAST_CHANNEL_ID)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(HOLDFAST_CHANNEL_ID)
            except discord.HTTPException:
                channel = None

        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "Application channel is unavailable. Please contact staff.",
                ephemeral=True,
            )

        app_id = _new_application_id(interaction.user.id)
        deadline_ts = int((_now_utc() + timedelta(hours=VOTE_DURATION_HOURS)).timestamp())

        embed = discord.Embed(
            title="New Community Application",
            description=f"Applicant: {interaction.user.mention}\nVoting closes: **{_fmt_deadline(deadline_ts)}**",
            color=discord.Color.green(),
            timestamp=_now_utc(),
        )
        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        for question, answer in answers.items():
            embed.add_field(name=question, value=answer or "No answer", inline=False)
        embed.add_field(name="Votes", value="Approve 0 | Reject 0 | Total 0", inline=False)
        embed.add_field(
            name="Decision Rules",
            value=f"Closes after {VOTE_DURATION_HOURS}h. Minimum {MIN_TOTAL_VOTES} total votes required.",
            inline=False,
        )

        vote_message = await channel.send(embed=embed, view=_build_vote_view(app_id))
        try:
            await vote_message.pin(reason="Auto-pinned community application")
        except discord.HTTPException:
            pass

        applications = _load_applications()
        applications[app_id] = {
            "applicant_id": interaction.user.id,
            "applicant_name": str(interaction.user),
            "guild_id": interaction.guild.id,
            "channel_id": vote_message.channel.id,
            "message_id": vote_message.id,
            "created_at_ts": _ts(),
            "deadline_ts": deadline_ts,
            "status": "pending",
            "answers": answers,
            "votes": {"approve": [], "reject": []},
            "result_reason": "",
        }
        _save_applications(applications)

        await interaction.response.send_message(
            "Your application was submitted successfully. The community can now vote on it.",
            ephemeral=True,
        )

    def _count_votes(self, app: dict) -> tuple[int, int, int]:
        votes = app.get("votes", {})
        approves = set(votes.get("approve", []))
        rejects = set(votes.get("reject", []))
        total = len(approves | rejects)
        return len(approves), len(rejects), total

    async def _update_vote_message(self, app_id: str, app: dict, close_view: bool = False) -> None:
        channel = self.bot.get_channel(int(app["channel_id"]))
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(int(app["channel_id"]))
            except discord.HTTPException:
                return
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            message = await channel.fetch_message(int(app["message_id"]))
        except discord.HTTPException:
            return

        embed = message.embeds[0] if message.embeds else discord.Embed(title="Application")
        approve_count, reject_count, total = self._count_votes(app)
        status = str(app.get("status", "pending")).replace("_", " ").title()

        votes_line = f"Approve {approve_count} | Reject {reject_count} | Total {total}"
        decision_line = f"Status: **{status}**"
        if app.get("result_reason"):
            decision_line += f"\nReason: {app['result_reason']}"

        found_votes = False
        found_decision = False
        for index, field in enumerate(embed.fields):
            if field.name == "Votes":
                embed.set_field_at(index, name="Votes", value=votes_line, inline=False)
                found_votes = True
            if field.name == "Decision":
                embed.set_field_at(index, name="Decision", value=decision_line, inline=False)
                found_decision = True
        if not found_votes:
            embed.add_field(name="Votes", value=votes_line, inline=False)
        if not found_decision:
            embed.add_field(name="Decision", value=decision_line, inline=False)

        await message.edit(embed=embed, view=_build_vote_view(app_id, disabled=close_view))

    async def _dm_result(self, app: dict) -> None:
        applicant_id = int(app.get("applicant_id", 0))
        if not applicant_id:
            return
        try:
            user = await self.bot.fetch_user(applicant_id)
        except discord.HTTPException:
            return

        status = str(app.get("status", "pending")).replace("_", " ").title()
        reason = app.get("result_reason", "")
        description = f"Your application status: **{status}**"
        if reason:
            description += f"\nReason: {reason}"
        embed = discord.Embed(
            title="Application Review Result",
            description=description,
            color=discord.Color.blurple(),
        )
        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            pass

    async def _finalize_if_due(self, app_id: str, app: dict) -> bool:
        if app.get("status") != "pending":
            return False
        if _ts() < int(app.get("deadline_ts", 0)):
            return False

        approve_count, reject_count, total = self._count_votes(app)

        if total < MIN_TOTAL_VOTES:
            app["status"] = "pending_review"
            app["result_reason"] = f"Not enough votes ({total}/{MIN_TOTAL_VOTES})."
        elif approve_count > reject_count:
            app["status"] = "approved"
            app["result_reason"] = "Community majority approved."
        elif reject_count > approve_count:
            app["status"] = "rejected"
            app["result_reason"] = "Community majority rejected."
        else:
            app["status"] = "pending_review"
            app["result_reason"] = "Tie vote. Manual follow-up required."

        await self._update_vote_message(app_id, app, close_view=True)
        await self._dm_result(app)
        return True

    @tasks.loop(minutes=1)
    async def review_pending(self) -> None:
        applications = _load_applications()
        changed = False
        for app_id, app in applications.items():
            changed = await self._finalize_if_due(app_id, app) or changed
        if changed:
            _save_applications(applications)

    @review_pending.before_loop
    async def before_review_pending(self) -> None:
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.type != discord.InteractionType.component:
            return

        data = interaction.data or {}
        custom_id = data.get("custom_id")
        if not isinstance(custom_id, str):
            return

        if custom_id == "apply:start":
            return await interaction.response.send_modal(ApplicationModal(self))

        if not custom_id.startswith("apply:vote:"):
            return

        parts = custom_id.split(":")
        if len(parts) != 4:
            return
        _, _, app_id, choice = parts
        if choice not in ("approve", "reject"):
            return

        applications = _load_applications()
        app = applications.get(app_id)
        if not app:
            return await interaction.response.send_message("This application was not found.", ephemeral=True)

        if app.get("status") != "pending":
            return await interaction.response.send_message("Voting is closed for this application.", ephemeral=True)

        if _ts() >= int(app.get("deadline_ts", 0)):
            await self._finalize_if_due(app_id, app)
            _save_applications(applications)
            return await interaction.response.send_message("Voting window has closed.", ephemeral=True)

        if interaction.user.bot:
            return await interaction.response.send_message("Bots cannot vote.", ephemeral=True)

        if int(app.get("applicant_id", 0)) == interaction.user.id:
            return await interaction.response.send_message("You cannot vote on your own application.", ephemeral=True)

        votes = app.setdefault("votes", {"approve": [], "reject": []})
        approve_set = set(votes.get("approve", []))
        reject_set = set(votes.get("reject", []))

        if choice == "approve":
            approve_set.add(interaction.user.id)
            reject_set.discard(interaction.user.id)
        else:
            reject_set.add(interaction.user.id)
            approve_set.discard(interaction.user.id)

        votes["approve"] = sorted(approve_set)
        votes["reject"] = sorted(reject_set)

        applications[app_id] = app
        _save_applications(applications)
        await self._update_vote_message(app_id, app)

        await interaction.response.send_message(
            f"Vote recorded: **{choice.capitalize()}**. You can change it until the deadline.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ApplyCog(bot))
