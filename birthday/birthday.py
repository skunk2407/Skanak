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


def _is_valid_day(month: int, day: int) -> bool:
    if month < 1 or month > 12:
        return False
    return 1 <= day <= MONTHS[month - 1][1]


class BirthdayView(View):
    def __init__(self, cog: "BirthdayCog", user_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.selected_month: Optional[int] = None
        self.selected_day: Optional[int] = None
        self.add_item(MonthSelect(self))
        self.add_item(DaySelect(self, start_day=1, end_day=15))
        self.add_item(DaySelect(self, start_day=16, end_day=31))
        self.add_item(SaveBirthdayButton(self))

    def summary(self) -> str:
        month_text = _month_name(self.selected_month) if self.selected_month else "not selected"
        day_text = str(self.selected_day) if self.selected_day else "not selected"
        return (
            "Set your birthday in 3 steps:\n"
            "1. Choose your month\n"
            "2. Choose your day from one of the day menus\n"
            "3. Click Save\n\n"
            f"Current selection: month = **{month_text}**, day = **{day_text}**"
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This birthday menu is not for you. Use `!birthday` to open your own.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True


class MonthSelect(Select):
    def __init__(self, birthday_view: BirthdayView):
        self.birthday_view = birthday_view
        options = [
            discord.SelectOption(label=name, value=str(index + 1))
            for index, (name, _) in enumerate(MONTHS)
        ]
        super().__init__(
            placeholder="Choose your birth month",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.birthday_view.selected_month = int(self.values[0])
        if self.birthday_view.selected_day and not _is_valid_day(
            self.birthday_view.selected_month, self.birthday_view.selected_day
        ):
            self.birthday_view.selected_day = None
        await interaction.response.edit_message(content=self.birthday_view.summary(), view=self.birthday_view)


class DaySelect(Select):
    def __init__(self, birthday_view: BirthdayView, *, start_day: int, end_day: int):
        self.birthday_view = birthday_view
        options = [discord.SelectOption(label=str(day), value=str(day)) for day in range(start_day, end_day + 1)]
        super().__init__(
            placeholder=f"Choose day {start_day}-{end_day}",
            min_values=1,
            max_values=1,
            options=options,
            row=1 if start_day == 1 else 2,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.birthday_view.selected_day = int(self.values[0])
        await interaction.response.edit_message(content=self.birthday_view.summary(), view=self.birthday_view)


class SaveBirthdayButton(Button):
    def __init__(self, birthday_view: BirthdayView):
        self.birthday_view = birthday_view
        super().__init__(label="Save Birthday", style=discord.ButtonStyle.success, row=3)

    async def callback(self, interaction: discord.Interaction) -> None:
        month = self.birthday_view.selected_month
        day = self.birthday_view.selected_day
        if month is None or day is None:
            return await interaction.response.send_message(
                "Choose both your month and your day before saving.",
                ephemeral=True,
            )
        if not _is_valid_day(month, day):
            return await interaction.response.send_message(
                "That day does not exist in the selected month. Please choose again.",
                ephemeral=True,
            )

        birthdays = _load_birthdays()
        user_id = str(interaction.user.id)
        was_existing = user_id in birthdays
        birthdays[user_id] = {
            "month": month,
            "day": day,
            "notified_years": [],
        }
        _save_birthdays(birthdays)

        for item in self.birthday_view.children:
            item.disabled = True

        status = "updated" if was_existing else "saved"
        await interaction.response.edit_message(
            content=f"Your birthday has been {status}: **{_month_name(month)} {day}**.",
            view=self.birthday_view,
        )


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

        await channel.send(f"Happy birthday, {user.mention}! We hope you have an amazing day.")

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
        prefix = "Choose or update your birthday below."
        if existing:
            prefix = (
                f"Your current birthday is **{_month_name(int(existing['month']))} {int(existing['day'])}**.\n"
                "Choose new values below if you want to update it."
            )

        view = BirthdayView(self, ctx.author.id)
        await ctx.send(f"{prefix}\n\n{view.summary()}", view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BirthdayCog(bot))
