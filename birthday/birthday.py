import os
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from storage.database import load_app_state, save_app_state

BIRTHDAYS_STATE_KEY = "birthday.birthdays"


def _birthday_channel_id():
    raw = os.getenv("BIRTHDAY_CHANNEL_ID", "")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


class BirthdayCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_birthdays.start()

    def cog_unload(self):
        self.check_birthdays.cancel()

    def load_birthdays(self):
        data = load_app_state(BIRTHDAYS_STATE_KEY, default={})
        return data if isinstance(data, dict) else {}

    def save_birthdays(self, birthdays):
        save_app_state(BIRTHDAYS_STATE_KEY, birthdays)

    def save_birthday(self, user_id, birthday_date):
        birthdays = self.load_birthdays()
        birthdays[user_id] = {"birthday": str(birthday_date), "notified_years": []}
        self.save_birthdays(birthdays)

    @tasks.loop(hours=24)
    async def check_birthdays(self):
        today = datetime.now().date()
        birthdays = self.load_birthdays()

        for user_id, birthday_data in birthdays.items():
            birthday_str = birthday_data.get("birthday")
            if not birthday_str:
                continue
            if self.birthday_today(birthday_str):
                if str(today.year) not in birthday_data.get("notified_years", []):
                    await self.send_birthday_message(user_id)
                    birthday_data.setdefault("notified_years", []).append(str(today.year))

        self.save_birthdays(birthdays)

    @check_birthdays.before_loop
    async def before_check_birthdays(self):
        await self.bot.wait_until_ready()

    def birthday_today(self, birthday_str):
        today = datetime.now().date()
        birthday_date = datetime.strptime(birthday_str, "%Y-%m-%d").date()
        return today.month == birthday_date.month and today.day == birthday_date.day

    async def send_birthday_message(self, user_id):
        channel_id = _birthday_channel_id()
        if not channel_id:
            return
        user = self.bot.get_user(int(user_id))
        channel = self.bot.get_channel(channel_id)
        if user and channel:
            await channel.send(f"HAPPY BIRTHDAAAAY {user.mention} 🎉🎂 !")

    @app_commands.command(name="birthday", description="Save your birthday date (format: YYYY-MM-DD)")
    async def set_birthday(self, interaction: discord.Interaction, date: str):
        channel_id = _birthday_channel_id()
        if not channel_id:
            return await interaction.response.send_message(
                "Birthday channel is not configured (`BIRTHDAY_CHANNEL_ID`).",
                ephemeral=True,
            )
        if interaction.channel.id != channel_id:
            await interaction.response.send_message("This command can be used only in the Birthday channel.", ephemeral=True)
            return

        try:
            birthday_date = datetime.strptime(date, "%Y-%m-%d").date()
            user_id = str(interaction.user.id)
            birthdays = self.load_birthdays()

            if user_id in birthdays:
                await interaction.response.send_message("Your birthday is already set. Use `/modify_birthday` to change it.", ephemeral=True)
            else:
                self.save_birthday(user_id, birthday_date)
                await interaction.response.send_message(f"Birthday saved for {interaction.user.name} 😎", ephemeral=True)
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send(f"🎉 {interaction.user.name} has saved their birthday! 🎉")
        except ValueError:
            await interaction.response.send_message("The date format is incorrect. Please use YYYY-MM-DD.", ephemeral=True)

    @app_commands.command(name="modify_birthday", description="Modify your birthday date (format: YYYY-MM-DD)")
    async def modify_birthday(self, interaction: discord.Interaction, new_date: str):
        channel_id = _birthday_channel_id()
        if not channel_id:
            return await interaction.response.send_message(
                "Birthday channel is not configured (`BIRTHDAY_CHANNEL_ID`).",
                ephemeral=True,
            )
        if interaction.channel.id != channel_id:
            await interaction.response.send_message("This command can be used only in the Birthday channel.", ephemeral=True)
            return

        try:
            new_birthday_date = datetime.strptime(new_date, "%Y-%m-%d").date()
            user_id = str(interaction.user.id)
            birthdays = self.load_birthdays()

            if user_id in birthdays:
                birthdays[user_id]["birthday"] = str(new_birthday_date)
                self.save_birthdays(birthdays)
                await interaction.response.send_message("Your birthday has been updated! 🎉", ephemeral=True)
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send(f"🎉 {interaction.user.name} has updated their birthday! 🎉")
            else:
                await interaction.response.send_message("No birthday found. Use `/birthday` to set your birthday.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("The date format is incorrect. Please use YYYY-MM-DD.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(BirthdayCog(bot))

