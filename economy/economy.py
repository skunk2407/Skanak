import os
import json
import random
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import BucketType

from .stats import load_stats, save_stats, get_user_stats
from .badges import BADGES, dispatch_badge_event

# ---------- Helpers ----------
def humanize(seconds: float) -> str:
    """Formatte 3661 -> '1h 1m' (ou '45m', '30s', '1d 2h 3m')."""
    s = max(0, int(seconds))
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    parts = []
    if d:
        parts.append(f"{d}d")
    if d or h:
        parts.append(f"{h}h")
    if d or h or m:
        parts.append(f"{m}m")
    else:
        parts.append(f"{s}s")
    return " ".join(parts)


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --------- Commands ----------
    @commands.command(name='work')
    async def work(self, ctx):
        stats = load_stats()
        user = get_user_stats(stats, ctx.author.id)
        now = datetime.utcnow()

        # Cooldown 2h
        if user['last_work']:
            last = datetime.fromisoformat(user['last_work'])
            rem = 7200 - (now - last).total_seconds()
            if rem > 0:
                return await ctx.send(f"⏳ Wait {humanize(rem)} to work again.")

        # Calcul du gain (+ multiplicateur)
        base = random.randint(0, 350)
        reward = int(base * user.get('next_work_multiplier', 1.0))
        user['next_work_multiplier'] = 1.0

        # Mise à jour des soldes/stats
        user['cheese'] += reward
        user['total_earned'] += reward
        user['last_work'] = now.isoformat()
        user['work_count'] = int(user.get('work_count', 0)) + 1
        user['cheese_since_last_spend'] = user.get('cheese_since_last_spend', 0) + reward

        # Record du plus gros gain au !work
        if reward > user.get('max_work_gain', 0):
            user['max_work_gain'] = reward

        # Speed Runner: enchaînement daily -> work < 60s
        prev = user.get('last_action')
        if prev == 'daily' and user.get('last_daily'):
            if (now - datetime.fromisoformat(user['last_daily'])).total_seconds() <= 60:
                user['quick_combo'] = user.get('quick_combo', 0) + 1
            else:
                user['quick_combo'] = 1
        else:
            user['quick_combo'] = 1
        user['last_action'] = 'work'

        save_stats(stats)

        await ctx.send(f"😃 {ctx.author.mention}, you worked and got **{reward}** 🧀.")

        # Badges (work)
        await dispatch_badge_event("work", ctx, user_state=user, stats=stats)

    @commands.command(name='daily')
    async def daily(self, ctx):
        stats = load_stats()
        user = get_user_stats(stats, ctx.author.id)
        now = datetime.utcnow()

        # Cooldown & reset streak
        if user['last_daily']:
            last = datetime.fromisoformat(user['last_daily'])
            if (now - last).days > 1:
                user['daily_streak'] = 0
            else:
                rem = 86400 - (now - last).total_seconds()
                if rem > 0:
                    return await ctx.send(f"⏳ Wait {humanize(rem)} for daily.")

        # Calcul du daily (+ progression de streak)
        if user['daily_streak'] < 30:
            reward = 100 + user['daily_streak'] * 25
            user['daily_streak'] += 1
        else:
            reward = 100
            user['daily_streak'] = 1

        reward = int(reward * user.get('next_daily_multiplier', 1.0))
        user['next_daily_multiplier'] = 1.0

        user['cheese'] += reward
        user['total_earned'] += reward
        user['last_daily'] = now.isoformat()
        user['daily_count'] = int(user.get('daily_count', 0)) + 1
        user['last_action'] = 'daily'
        user['cheese_since_last_spend'] = user.get('cheese_since_last_spend', 0) + reward

        save_stats(stats)

        await ctx.send(f"🎉 {ctx.author.mention}, you claimed **{reward}** 🧀! Streak: {user['daily_streak']}")

        # Badges (daily)
        await dispatch_badge_event("daily", ctx, user_state=user, stats=stats)

    @commands.command(name='share')
    async def share(self, ctx, member: discord.Member, amount: int):
        stats = load_stats()
        sender = get_user_stats(stats, ctx.author.id)
        receiver = get_user_stats(stats, member.id)

        if amount <= 0:
            return await ctx.send("❌ Amount must be positive.")
        if sender['cheese'] < amount:
            return await ctx.send("❌ You don't have enough cheese.")

        sender['cheese'] -= amount
        receiver['cheese'] += amount
        receiver['cheese_since_last_spend'] = receiver.get('cheese_since_last_spend', 0) + amount
        sender['total_shared'] = sender.get('total_shared', 0) + amount
        sender['share_count'] = int(sender.get('share_count', 0)) + 1

        save_stats(stats)

        await ctx.send(f"🤝 {ctx.author.mention} shared **{amount}** 🧀 with {member.mention}!")

        # Badges (share)
        await dispatch_badge_event(
            "share", ctx,
            sender_state=sender, receiver_state=receiver, amount=amount, stats=stats
        )

    @commands.command(name='inventory')
    async def inventory(self, ctx):
        """Show your active boosts, shields and consumables."""
        stats = load_stats()
        u = get_user_stats(stats, ctx.author.id)
        now_ts = datetime.utcnow().timestamp()

        shield = "none"
        if u.get('safe_mode_permanent'):
            shield = "🛡️ Permanent"
        elif u.get('safe_mode_expiry', 0) > now_ts:
            remain = u['safe_mode_expiry'] - now_ts
            shield = f"🛡️ {humanize(remain)} left"

        fields = {
            "🛡️ Shield": shield,
            "⚡ Next `!work` multiplier": f"x{u.get('next_work_multiplier', 1.0)}",
            "⚡ Next `!daily` multiplier": f"x{u.get('next_daily_multiplier', 1.0)}",
            "🗡️ Next `!steal` boost": f"+{int(u.get('steal_boost', 0.0)*100)}%",
            "🧨 Trap Cheese (charges)": str(u.get('trap_cheese_charges', 0)),
            "🔄 Counter-Steal (charges)": str(u.get('counter_steal_charges', 0)),
            "✏️ Rename tokens": str(u.get('rename_tokens', 0)),
        }

        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Inventory",
            color=discord.Color.blurple()
        )
        if ctx.author.avatar:
            embed.set_thumbnail(url=ctx.author.avatar.url)
        for k, v in fields.items():
            embed.add_field(name=k, value=v, inline=False)

        await ctx.send(embed=embed)

    @commands.command(name='gamble')
    async def gamble(self, ctx, amount: int):
        """🎲 Gamble your cheese! 50/50 chance to double or lose everything."""
        stats = load_stats()
        user = get_user_stats(stats, ctx.author.id)

        # Limites
        MAX_BET = 5000
        MIN_BET = 10

        if amount < MIN_BET:
            return await ctx.send(f"❌ Minimum bet is {MIN_BET:,} 🧀.")
        if user['cheese'] < amount:
            return await ctx.send("❌ You don’t have that much cheese.")
        if amount > MAX_BET:
            return await ctx.send(f"❌ You can’t bet more than {MAX_BET:,} 🧀 at once.")

        # Résultat (50/50)
        if random.random() < 0.5:
            winnings = amount
            user['cheese'] += winnings
            msg = f"🎉 {ctx.author.mention} won **{winnings}** 🧀! Balance: {user['cheese']:,} 🧀"
        else:
            user['cheese'] -= amount
            msg = f"💀 {ctx.author.mention} lost **{amount}** 🧀... Balance: {user['cheese']:,} 🧀"

        save_stats(stats)
        await ctx.send(msg)

    @commands.command(name='steal')
    @commands.cooldown(1, 86400, BucketType.user)
    async def steal(self, ctx, target: discord.Member):
        stats = load_stats()
        thief = get_user_stats(stats, ctx.author.id)
        victim = get_user_stats(stats, target.id)
        now_ts = datetime.utcnow().timestamp()

        if target == ctx.author:
            return await ctx.send("❌ You can't steal from yourself.")
        if victim['cheese'] <= 0:
            return await ctx.send(f"❌ {target.mention} has no cheese to steal.")

        # Compteur “raid boss”
        if now_ts - victim.get('last_stolen_time', 0.0) <= 86400:
            victim['consecutive_stolen_count'] = victim.get('consecutive_stolen_count', 0) + 1
        else:
            victim['consecutive_stolen_count'] = 1
        victim['last_stolen_time'] = now_ts

        save_stats(stats)
        await dispatch_badge_event(
            "steal", ctx,
            thief_state=thief, victim_state=victim, stolen=0,
            stats=stats, victim_member=target
        )

        # Bouclier ?
        if victim.get('safe_mode_permanent') or victim.get('safe_mode_expiry', 0) > now_ts:
            return await ctx.send(f"🛡️ {target.mention} is shielded.")

        # Base du vol
        base = random.randint(0, 500)
        stolen = int(base * thief.get('steal_boost', 0.0) + base)
        thief['steal_boost'] = 0.0
        stolen = min(stolen, victim['cheese'])

        if stolen > 0:
            # 1) Trap Cheese
            if victim.get('trap_cheese_charges', 0) > 0:
                victim['trap_cheese_charges'] -= 1
                penalty = min(thief['cheese'], max(50, base))
                thief['cheese'] -= penalty
                save_stats(stats)
                return await ctx.send(
                    f"🧨 Trap Cheese! {ctx.author.mention} triggered a trap and lost **{penalty}** 🧀 instead."
                )

            # Vol réussi
            victim['cheese'] -= stolen
            thief['cheese'] += stolen
            thief['cheese_since_last_spend'] = thief.get('cheese_since_last_spend', 0) + stolen
            thief['total_stolen'] = thief.get('total_stolen', 0) + stolen

            tv = thief.get('theft_victims', [])
            if target.id not in tv:
                tv.append(target.id)
                thief['theft_victims'] = tv

            save_stats(stats)
            await ctx.send(f"💰 {ctx.author.mention} stole **{stolen}** 🧀 from {target.mention}!")

            # 2) Counter-Steal
            if victim.get('counter_steal_charges', 0) > 0:
                victim['counter_steal_charges'] -= 1
                counter = min(stolen, thief['cheese'])
                thief['cheese'] -= counter
                victim['cheese'] += counter
                save_stats(stats)
                await ctx.send(
                    f"🔄 Counter-Steal! {target.mention} retaliated and recovered **{counter}** 🧀."
                )

            await dispatch_badge_event(
                "steal", ctx,
                thief_state=thief, victim_state=victim, stolen=stolen,
                stats=stats, victim_member=target
            )
        else:
            await ctx.send(f"😢 {ctx.author.mention} got caught!")

    @steal.error
    async def steal_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ You can steal again in {humanize(error.retry_after)}.")

    @commands.command()
    @commands.is_owner()
    async def grant(self, ctx, badge_key: str, member: discord.Member = None):
        """Commande de test/administration : annonce visuelle d'un badge."""
        meta = BADGES.get(badge_key)
        target = member or ctx.author
        if not meta:
            return await ctx.send("❌ Unknown badge.")
        embed = discord.Embed(
            title="🛠️ Test Badge Unlocked!",
            description=f"{target.mention} earned **{meta['name']}**!",
            color=discord.Color.purple()
        )
        if meta.get("url"):
            embed.set_thumbnail(url=meta["url"])
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Economy(bot))
