import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

import discord
from discord.ext import commands

# --- Helper to safely parse environment variables into ints ---
def _to_int(env_key: str):
    v = os.getenv(env_key)
    try:
        return int(v) if v else None
    except ValueError:
        return None

# --- Environment variables (from .env file) ---
MESSAGE_LOG_CH_ID = _to_int("MESSAGE_LOG_CHANNEL_ID")
BAN_LOG_CH_ID = _to_int("BAN_LOG_CHANNEL_ID")
JOIN_LEAVE_LOG_CH_ID = _to_int("JOIN_LEAVE_LOG_CHANNEL_ID")  # optional
VOICE_LOG_CH_ID = _to_int("VOICE_LOG_CHANNEL_ID")
MASS_MENTION_THRESHOLD = int(os.getenv("MASS_MENTION_THRESHOLD", "5"))

class ModLogs(commands.Cog):
    """Moderation logs system for message deletes, bans, voice events, etc."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Simple local SQLite database to store messages
        self.conn = sqlite3.connect("message_log.db")
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY,
                guild_id INTEGER,
                channel_id INTEGER,
                author_id INTEGER,
                author_name TEXT,
                content TEXT,
                attachments TEXT,
                created_at TEXT
            )
        ''')
        self.conn.commit()

    # --- Database helpers ---

    def save_message(self, m: discord.Message):
        """Save every message in the database for traceability."""
        atts = ",".join(a.url for a in m.attachments) if m.attachments else ""
        self.conn.execute('''
            INSERT OR REPLACE INTO messages
            (message_id, guild_id, channel_id, author_id, author_name, content, attachments, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            m.id, m.guild.id if m.guild else None, m.channel.id,
            m.author.id, str(m.author), m.content, atts,
            m.created_at.isoformat()
        ))
        self.conn.commit()

    def fetch_message(self, message_id: int):
        """Get a message by its ID from the database."""
        cur = self.conn.execute('SELECT * FROM messages WHERE message_id=?', (message_id,))
        return cur.fetchone()

    def fetch_recent_by_user(self, guild_id: int, user_id: int, limit: int = 6):
        """Fetch the latest messages sent by a specific user."""
        cur = self.conn.execute('''
            SELECT * FROM messages
            WHERE guild_id=? AND author_id=?
            ORDER BY created_at DESC LIMIT ?
        ''', (guild_id, user_id, limit))
        return cur.fetchall()

    # --- Utility ---

    def get_channel(self, channel_id: Optional[int]):
        """Shortcut to safely get a channel by ID."""
        return self.bot.get_channel(channel_id) if channel_id else None

    # --- Event listeners ---

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Triggered on every message creation."""
        if not message.guild or message.author.bot:
            return

        # Save all messages (used later if deleted or for ban context)
        self.save_message(message)

        # Detect mass mentions (ping spam)
        if MESSAGE_LOG_CH_ID:
            if message.mention_everyone or len(message.mentions) >= MASS_MENTION_THRESHOLD:
                ch = self.get_channel(MESSAGE_LOG_CH_ID)
                if ch:
                    emb = discord.Embed(
                        title="⚠️ Mass mention detected",
                        color=0xFFCC00,
                        timestamp=datetime.now(timezone.utc)
                    )
                    emb.add_field(name="Author", value=f"{message.author} ({message.author.id})", inline=False)
                    emb.add_field(name="Channel", value=message.channel.mention, inline=True)
                    emb.add_field(name="Mentions", value=f"everyone: {message.mention_everyone} | count: {len(message.mentions)}", inline=True)
                    emb.add_field(name="Content", value=message.content[:1000] or "(embed/attachment)", inline=False)
                    await ch.send(embed=emb)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Triggered when a message is deleted."""
        if not MESSAGE_LOG_CH_ID:
            return
        ch = self.get_channel(MESSAGE_LOG_CH_ID)
        if not ch:
            return

        row = self.fetch_message(message.id) if message and message.id else None
        if not row:
            # No data found (maybe bot offline when message was sent)
            emb = discord.Embed(
                title="🗑️ Message deleted (details unavailable)",
                description=f"ID: {message.id}",
                color=0xFF0000,
                timestamp=datetime.now(timezone.utc)
            )
            await ch.send(embed=emb)
            return

        _, guild_id, channel_id, author_id, author_name, content, attachments, created_at = row
        emb = discord.Embed(
            title="🗑️ Message deleted",
            color=0xFF0000,
            timestamp=datetime.now(timezone.utc)
        )
        emb.add_field(name="Author", value=f"{author_name} ({author_id})", inline=False)
        emb.add_field(name="Channel", value=f"<#{channel_id}>", inline=True)
        emb.add_field(name="Created at", value=created_at, inline=True)
        if content:
            emb.add_field(name="Content", value=content[:1000], inline=False)
        if attachments:
            emb.add_field(name="Attachments", value=attachments, inline=False)
        await ch.send(embed=emb)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        """Triggered when multiple messages are deleted at once."""
        if not MESSAGE_LOG_CH_ID or not messages:
            return
        ch = self.get_channel(MESSAGE_LOG_CH_ID)
        if not ch:
            return
        emb = discord.Embed(
            title="🧹 Bulk message delete",
            description=f"{len(messages)} messages deleted",
            color=0xFF6600,
            timestamp=datetime.now(timezone.utc)
        )
        await ch.send(embed=emb)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Triggered when a user gets banned."""
        if not BAN_LOG_CH_ID:
            return
        ch = self.get_channel(BAN_LOG_CH_ID)
        if not ch:
            return

        emb = discord.Embed(
            title="🔨 Member banned",
            color=0x990000,
            timestamp=datetime.now(timezone.utc)
        )
        emb.add_field(name="User", value=f"{user} ({user.id})", inline=False)

        # Include last messages from that user for context
        rows = self.fetch_recent_by_user(guild.id, user.id, limit=6)
        if rows:
            txt = ""
            for row in rows:
                _, _, channel_id, _, _, content, attachments, created_at = row
                line = f"<#{channel_id}> • {created_at} • {content[:200] if content else '(file/embed)'}"
                if attachments:
                    line += " • [attachments]"
                txt += line + "\n"
            emb.add_field(name="Recent messages", value=txt[:1000], inline=False)
        await ch.send(embed=emb)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Triggered when a user joins, leaves, or switches voice channels."""
        ch = self.get_channel(VOICE_LOG_CH_ID)
        if not ch:
            return
        if before.channel != after.channel:
            b = before.channel.mention if before.channel else "∅"
            a = after.channel.mention if after.channel else "∅"
            await ch.send(f"🎙️ **{member}**: {b} ➜ {a}")

# --- Cog setup function ---
async def setup(bot: commands.Bot):
    await bot.add_cog(ModLogs(bot))
