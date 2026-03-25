from datetime import datetime
from typing import Dict, Optional

import discord
from discord.ext import commands, tasks
from discord.ui import Button, Select, View

from storage.database import load_app_state, save_app_state

BIRTHDAY_CHANNEL_ID = 577913608323727362
BIRTHDAY_STATE_KEY = "birthday.entries"

MONTHS = [
    ("January", 31),
    ("February", 29),
    ("March", 31),
    ("April", 30),
    ("May", 31),
    ("June", 30),
    ("July", 31),
    ("August", 31),
    ("September", 30),
    ("October", 31),
    ("November", 30),
    ("December", 31),
]


def _load_birthdays() -> Dict[str, dict]:
    data = load_app_state(BIRTHDAY_STATE_KEY, default={})
    return data if isinstance(data, dict) else {}


def _save_birthdays(data: Dict[str, dict]) -> None:
    save_app_state(BIRTHDAY_STATE_KEY, data)


def _month_name(month: int) -> str:
    return MONTHS[month - 1][0]


def _days_in_month(month: int) -> int:
    return MONTHS[month - 1][1]


def _is_valid_day(month: int, day: int) -> bool:
    if month < 1 or month > 12:
        return False
    return 1 <= day <= _days_in_month(month)


def _page_start_for_day(day: Optional[int]) -> int:
    if not day or day <= 25:
        return 1
    return ((day - 1) // 25) * 25 + 1


class MonthSelect(Select):
    def __init__(self, birthday_view: "BirthdayView"):
        self.birthday_view = birthday_view
        options = []
        for index, (name, _) in enumerate(MONTHS, start=1):
            options.append(
                discord.SelectOption(
                    label=name,
                    value=str(index),
                    default=index == birthday_view.selected_month,
                )
            )

        placeholder = "Choose your birth month"
        if birthday_view.selected_month:
            placeholder = f"Month: {_month_name(birthday_view.selected_month)}"

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.birthday_view.selected_month = int(self.values[0])
        self.birthday_view.day_page_start = _page_start_for_day(self.birthday_view.selected_day)
        if self.birthday_view.selected_day and not _is_valid_day(
            self.birthday_view.selected_month, self.birthday_view.selected_day
        ):
            self.birthday_view.selected_day = None
            self.birthday_view.day_page_start = 1
        self.birthday_view.refresh_components()
        await interaction.response.edit_message(content=self.birthday_view.summary(), view=self.birthday_view)


class DaySelect(Select):
    def __init__(self, birthday_view: "BirthdayView"):
        self.birthday_view = birthday_view
        month = birthday_view.selected_month

        if month is None:
            options = [discord.SelectOption(label="Choose a month first", value="0")]
            placeholder = "Choose your day"
            disabled = True
        else:
            max_day = _days_in_month(month)
            start_day = min(birthday_view.day_page_start, max_day)
            end_day = min(start_day + 24, max_day)
            options = [
                discord.SelectOption(
                    label=str(day),
                    value=str(day),
                    default=day == birthday_view.selected_day,
                )
                for day in range(start_day, end_day + 1)
            ]
            if birthday_view.selected_day:
                placeholder = f"Day: {birthday_view.selected_day}"
            elif start_day == 1 and end_day == max_day:
                placeholder = "Choose your day"
            else:
                placeholder = f"Choose your day ({start_day}-{end_day})"
            disabled = False

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
            disabled=disabled,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.birthday_view.selected_day = int(self.values[0])
        self.birthday_view.day_page_start = _page_start_for_day(self.birthday_view.selected_day)
        self.birthday_view.refresh_components()
        await interaction.response.edit_message(content=self.birthday_view.summary(), view=self.birthday_view)


class DayPageButton(Button):
    def __init__(self, birthday_view: "BirthdayView", *, direction: int):
        self.birthday_view = birthday_view
        self.direction = direction
        month = birthday_view.selected_month
        disabled = month is None

        if month is not None:
            max_day = _days_in_month(month)
            if direction < 0:
                disabled = birthday_view.day_page_start <= 1
            else:
                disabled = birthday_view.day_page_start + 25 > max_day

        label = "Previous Days" if direction < 0 else "Next Days"
        style = discord.ButtonStyle.secondary
        super().__init__(label=label, style=style, disabled=disabled, row=2)

    async def callback(self, interaction: discord.Interaction) -> None:
        month = self.birthday_view.selected_month
        if month is None:
            return await interaction.response.send_message("📅 Choose your month first.", ephemeral=True)

        max_day = _days_in_month(month)
        new_start = self.birthday_view.day_page_start + (25 * self.direction)
        self.birthday_view.day_page_start = max(1, min(new_start, _page_start_for_day(max_day)))
        self.birthday_view.refresh_components()
        await interaction.response.edit_message(content=self.birthday_view.summary(), view=self.birthday_view)


class SaveBirthdayButton(Button):
    def __init__(self, birthday_view: "BirthdayView"):
        self.birthday_view = birthday_view
        label = "Update Birthday" if birthday_view.had_existing_birthday else "Save Birthday"
        super().__init__(label=label, style=discord.ButtonStyle.success, row=3)

    async def callback(self, interaction: discord.Interaction) -> None:
        month = self.birthday_view.selected_month
        day = self.birthday_view.selected_day

        if month is None or day is None:
            return await interaction.response.send_message(
                "🎂 Choose your month and your day before saving.",
                ephemeral=True,
            )
        if not _is_valid_day(month, day):
            return await interaction.response.send_message(
                "⚠️ That day does not exist in the selected month.",
                ephemeral=True,
            )

        birthdays = _load_birthdays()
        user_id = str(interaction.user.id)
        status = "updated" if user_id in birthdays else "saved"
        birthdays[user_id] = {
            "month": month,
            "day": day,
            "notified_years": [],
        }
        _save_birthdays(birthdays)

        self.birthday_view.had_existing_birthday = True
        for item in self.birthday_view.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=(
                f"🎉 Your birthday was {status}: **{_month_name(month)} {day}**.\n"
                "You can use `!birthday` again anytime to change it."
            ),
            view=self.birthday_view,
        )


class BirthdayView(View):
    def __init__(
        self,
        user_id: int,
        *,
        existing_month: Optional[int] = None,
        existing_day: Optional[int] = None,
    ):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.selected_month = existing_month
        self.selected_day = existing_day
        self.day_page_start = _page_start_for_day(existing_day)
        self.had_existing_birthday = existing_month is not None and existing_day is not None
        self.refresh_components()

    def refresh_components(self) -> None:
        self.clear_items()
        self.add_item(MonthSelect(self))
        self.add_item(DaySelect(self))
        self.add_item(DayPageButton(self, direction=-1))
        self.add_item(DayPageButton(self, direction=1))
        self.add_item(SaveBirthdayButton(self))

    def summary(self) -> str:
        month_text = _month_name(self.selected_month) if self.selected_month else "not selected"
        day_text = str(self.selected_day) if self.selected_day else "not selected"
        base = (
            "Pick your month, then your day, then click the green button to save.\n"
            "Running `!birthday` again will replace your old birthday.\n\n"
            f"Current selection: **{month_text} {day_text}**"
        )
        if self.selected_month and _days_in_month(self.selected_month) > 25:
            base += "\nIf you do not see your day, use **Previous Days** or **Next Days**."
        return base

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "🎂 This birthday menu is not for you. Use `!birthday` to open your own.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True


class BirthdayCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_birthdays.start()

    def cog_unload(self) -> None:
        self.check_birthdays.cancel()

    async def _get_birthday_channel(self) -> Optional[discord.TextChannel]:
        channel = self.bot.get_channel(BIRTHDAY_CHANNEL_ID)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(BIRTHDAY_CHANNEL_ID)
            except discord.HTTPException:
                return None
        return channel if isinstance(channel, discord.TextChannel) else None

    async def send_birthday_message(self, user_id: str) -> None:
        channel = await self._get_birthday_channel()
        if not channel:
            return

        user = self.bot.get_user(int(user_id))
        if user is None:
            try:
                user = await self.bot.fetch_user(int(user_id))
            except discord.HTTPException:
                return

        await channel.send(f"🎂 Happy birthday, {user.mention}! We hope you have an amazing day!")

    @tasks.loop(hours=1)
    async def check_birthdays(self) -> None:
        today = datetime.utcnow().date()
        birthdays = _load_birthdays()
        changed = False

        for user_id, entry in birthdays.items():
            month = int(entry.get("month", 0) or 0)
            day = int(entry.get("day", 0) or 0)
            if month != today.month or day != today.day:
                continue

            notified_years = entry.setdefault("notified_years", [])
            if str(today.year) in notified_years:
                continue

            await self.send_birthday_message(user_id)
            notified_years.append(str(today.year))
            changed = True

        if changed:
            _save_birthdays(birthdays)

    @check_birthdays.before_loop
    async def before_check_birthdays(self) -> None:
        await self.bot.wait_until_ready()

    @commands.command(name="birthday")
    async def birthday(self, ctx: commands.Context) -> None:
        birthdays = _load_birthdays()
        existing = birthdays.get(str(ctx.author.id))
        existing_month = int(existing["month"]) if existing else None
        existing_day = int(existing["day"]) if existing else None

        if existing:
            intro = (
                f"🎉 Your saved birthday is **{_month_name(existing_month)} {existing_day}**.\n"
                "Choose a new date below if you want to replace it."
            )
        else:
            intro = "🎂 Set your birthday below."

        view = BirthdayView(
            ctx.author.id,
            existing_month=existing_month,
            existing_day=existing_day,
        )
        await ctx.send(f"{intro}\n\n{view.summary()}", view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BirthdayCog(bot))
