import json
import sqlite3

import discord
from discord.ext import commands, tasks

from storage.database import DATABASE_PATH

GENERAL_CHANNEL_ID = 577913608323727362


class WebEconomyNotifications(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.deliver.start()

    def cog_unload(self) -> None:
        self.deliver.cancel()

    @tasks.loop(seconds=8, reconnect=True)
    async def deliver(self) -> None:
        with sqlite3.connect(DATABASE_PATH, timeout=5) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("CREATE TABLE IF NOT EXISTS economy_notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, payload TEXT NOT NULL, delivered_at TEXT NULL, created_at TEXT NOT NULL)")
            rows = connection.execute(
                "SELECT id, payload FROM economy_notifications WHERE type = 'web_steal' AND delivered_at IS NULL ORDER BY id LIMIT 10"
            ).fetchall()

        if not rows:
            return
        channel = self.bot.get_channel(GENERAL_CHANNEL_ID)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(GENERAL_CHANNEL_ID)
            except discord.DiscordException:
                return

        for row in rows:
            payload = json.loads(row["payload"])
            thief = "**an anonymous operative**" if payload.get("anonymous") else f'<@{payload["thief_id"]}>'
            victim = f'<@{payload["victim_id"]}>'
            amount = int(payload.get("amount", 0))
            status = payload.get("status")
            messages = {
                "success": f"🚨 **VAULT BREACH!** {victim}, your defenses have fallen, {thief} infiltrated your vault and escaped with **{amount:,} Cheese**! 🧀",
                "countered": f"🔄 **HEIST REVERSED!** {thief} breached {victim}'s vault, but a Counter-Steal activated and recovered all **{amount:,} Cheese**!",
                "trapped": f"🧨 **TRAP DETONATED!** {thief} attempted to raid {victim}'s vault and triggered Trap Cheese, losing **{amount:,} Cheese** in the blast!",
                "shielded": f"🛡️ **ACCESS DENIED!** {thief} launched a heist against {victim}, but the vault shield held firm!",
                "caught": f"🚓 **INTRUDER SPOTTED!** {thief} tried to break into {victim}'s vault, but escaped the scene empty-handed!",
            }
            try:
                await channel.send(messages.get(status, f"🧀 A web heist involving {thief} and {victim} has ended."), allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))
            except discord.DiscordException:
                continue
            with sqlite3.connect(DATABASE_PATH, timeout=5) as connection:
                connection.execute("UPDATE economy_notifications SET delivered_at = datetime('now') WHERE id = ? AND delivered_at IS NULL", (row["id"],))
                connection.commit()

    @deliver.before_loop
    async def before_deliver(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WebEconomyNotifications(bot))
