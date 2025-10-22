import os
import json
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord.ext import commands, tasks

from .stats import load_stats, save_stats, get_user_stats

LOTT_PATH = os.path.join(os.path.dirname(__file__), "lottery.json")
RENAMES_PATH = os.path.join(os.path.dirname(__file__), "renames.json")

def _load_json(path: str):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_json(path: str, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def humanize(seconds: float) -> str:
    s = max(0, int(seconds))
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if d or h: parts.append(f"{h}h")
    if d or h or m: parts.append(f"{m}m")
    else: parts.append(f"{s}s")
    return " ".join(parts)


class EconomyExtras(commands.Cog):
    """
    Extras d'économie :
    - Lottery: !lottery (info), !lottery_draw (admin)
    - Rename: !rename, !unrename (admin), auto-revert toutes les heures
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Démarre une tâche qui vérifie les pseudos expirés
        self.rename_sweeper.start()

    def cog_unload(self):
        self.rename_sweeper.cancel()

    # ---------------- LISTENER RENAME LOCK ----------------
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Empêche un membre renommé de contourner son rename avant l’expiration."""
        if before.nick == after.nick:
            return
        if after.guild is None:
            return

        renames = _load_json(RENAMES_PATH)
        gid = str(after.guild.id)
        uid = str(after.id)
        data = renames.get(gid, {}).get(uid)
        if not data:
            return

        now_ts = datetime.utcnow().timestamp()
        exp = float(data.get("expires_at", 0))
        desired = data.get("new_nick")

        if not desired or now_ts >= exp:
            return
        if after.nick == desired:
            return

        try:
            await after.edit(nick=desired, reason="Rename lock active (24h)")
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

    # ---------------- LOTTERY ----------------
    @commands.command(name="lottery")
    async def lottery_info(self, ctx: commands.Context):
        """Afficher l'état de la loterie du serveur (tickets & pot estimé)."""
        lotto = _load_json(LOTT_PATH)
        gid = str(ctx.guild.id) if ctx.guild else "global"
        entries = lotto.get(gid, [])
        pot = int(len(entries) * 500 * 0.9)

        unique = {}
        for uid in entries:
            unique[uid] = unique.get(uid, 0) + 1

        if not entries:
            return await ctx.send("🎟️ No tickets yet. Buy one in the shop to join the pot!")

        lines = []
        show = list(unique.items())[:10]
        for uid, cnt in show:
            m = ctx.guild.get_member(int(uid)) if ctx.guild else None
            name = m.mention if m else f"`{uid}`"
            lines.append(f"{name} — {cnt} 🎟️")

        desc = "\n".join(lines)
        more = max(0, len(unique) - len(show))
        if more:
            desc += f"\n…and **{more}** more players."

        embed = discord.Embed(
            title="🎰 Lottery — Current Pot",
            description=desc or "(no entries)",
            color=discord.Color.gold()
        )
        embed.add_field(name="Tickets sold", value=str(len(entries)))
        embed.add_field(name="Estimated pot", value=f"**{pot:,}** 🧀")
        if ctx.guild and ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.send(embed=embed)

    @commands.command(name="lottery_draw")
    @commands.has_permissions(manage_guild=True)
    async def lottery_draw(self, ctx: commands.Context, jackpot: Optional[int] = None):
        """Tirer le gagnant de la loterie (admin)."""
        lotto = _load_json(LOTT_PATH)
        gid = str(ctx.guild.id) if ctx.guild else "global"
        entries = lotto.get(gid, [])

        if not entries:
            return await ctx.send("❌ No tickets to draw.")

        if jackpot is None:
            jackpot = int(len(entries) * 500 * 0.9)
            jackpot = max(jackpot, 500)

        winner_uid = int(random.choice(entries))
        winner = ctx.guild.get_member(winner_uid) if ctx.guild else None

        stats = load_stats()
        entry = get_user_stats(stats, winner_uid)
        entry['cheese'] = entry.get('cheese', 0) + int(jackpot)
        save_stats(stats)

        lotto[gid] = []
        _save_json(LOTT_PATH, lotto)

        if winner:
            await ctx.send(f"🎉 **Lottery Winner:** {winner.mention} wins **{jackpot:,}** 🧀! GG!")
        else:
            await ctx.send(f"🎉 **Lottery Winner:** <@{winner_uid}> wins **{jackpot:,}** 🧀! GG!")

    @lottery_draw.error
    async def lottery_draw_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need `Manage Server` to draw the lottery.")

    # ---------------- RENAME ----------------
    @commands.command(name="rename")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def rename_member(self, ctx: commands.Context, member: discord.Member, *, new_nick: str):
        """Utiliser 1 token de rename pour renommer un membre pendant 24h (protégé des renames)."""
        if member == ctx.author:
            return await ctx.send("❌ You can't rename yourself.")
        if member.bot:
            return await ctx.send("❌ You can't rename bots.")
        if not ctx.guild.me.guild_permissions.manage_nicknames:
            return await ctx.send("❌ I need `Manage Nicknames` permission.")
        if len(new_nick) > 32:
            return await ctx.send("❌ Nickname too long (max 32 chars).")

        renames = _load_json(RENAMES_PATH)
        gid = str(ctx.guild.id)
        uid = str(member.id)
        existing = renames.get(gid, {}).get(uid)
        now_ts = datetime.utcnow().timestamp()
        if existing and now_ts < float(existing.get("expires_at", 0)):
            remain = float(existing["expires_at"]) - now_ts
            return await ctx.send(
                f"❌ {member.mention} cannot be renamed right now (already renamed). "
                f"Time left: **{humanize(remain)}**."
            )

        stats = load_stats()
        user = get_user_stats(stats, ctx.author.id)
        tokens = int(user.get('rename_tokens', 0))
        if tokens <= 0:
            return await ctx.send("❌ You don't have a rename token. Buy one in the shop.")

        user['rename_tokens'] = tokens - 1

        old = member.nick or member.name
        expires_at = (datetime.utcnow() + timedelta(hours=24)).timestamp()

        renames.setdefault(gid, {})
        renames[gid][uid] = {
            "old_nick": old,
            "new_nick": new_nick,
            "set_by": str(ctx.author.id),
            "expires_at": expires_at
        }

        try:
            await member.edit(nick=new_nick, reason=f"Rename token by {ctx.author}")
        except discord.Forbidden:
            return await ctx.send("❌ I don't have permission to rename that member (role hierarchy).")

        save_stats(stats)
        _save_json(RENAMES_PATH, renames)

        await ctx.send(
            f"✏️ {member.mention} renamed to **{discord.utils.escape_markdown(new_nick)}** for 24h. "
            f"(Protected from other renames)"
        )

    @commands.command(name="unrename")
    @commands.has_permissions(manage_nicknames=True)
    async def unrename(self, ctx: commands.Context, member: discord.Member):
        """Admin: revert le pseudo d'un membre si un rename est actif/expiré."""
        renames = _load_json(RENAMES_PATH)
        gid = str(ctx.guild.id)
        uid = str(member.id)
        data = renames.get(gid, {}).get(uid)
        if not data:
            return await ctx.send("ℹ️ No rename record for this member.")

        old_nick = data.get("old_nick") or member.name
        try:
            await member.edit(nick=old_nick, reason="Manual unrename")
        except discord.Forbidden:
            return await ctx.send("❌ I don't have permission to edit that member.")

        del renames[gid][uid]
        if not renames[gid]:
            del renames[gid]
        _save_json(RENAMES_PATH, renames)
        await ctx.send(f"↩️ Restored nickname for {member.mention}.")

    # ---------------- RENAME SWEEPER ----------------
    @tasks.loop(minutes=30)
    async def rename_sweeper(self):
        await self.bot.wait_until_ready()
        renames = _load_json(RENAMES_PATH)
        if not renames:
            return
        now_ts = datetime.utcnow().timestamp()

        dirty = False
        for gid, users in list(renames.items()):
            guild = self.bot.get_guild(int(gid))
            if not guild:
                continue
            for uid, data in list(users.items()):
                exp = float(data.get("expires_at", 0))
                if now_ts >= exp:
                    member = guild.get_member(int(uid))
                    if not member:
                        del users[uid]
                        dirty = True
                        continue
                    old_nick = data.get("old_nick") or member.name
                    try:
                        await member.edit(nick=old_nick, reason="Auto unrename (expired)")
                    except discord.Forbidden:
                        pass
                    del users[uid]
                    dirty = True
            if not users:
                del renames[gid]

        if dirty:
            _save_json(RENAMES_PATH, renames)

    @rename_sweeper.before_loop
    async def before_rename_sweeper(self):
        await asyncio.sleep(5)


async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyExtras(bot))
