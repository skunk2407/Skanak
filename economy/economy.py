import random
from datetime import datetime

import discord
from discord.ext import commands

from .badges import BADGES, dispatch_badge_event
from .stats import get_user_stats, load_stats, save_stats
from storage.database import load_app_state, save_app_state
from storage.daily import claim_daily
from storage.work import claim_work

STEAL_COOLDOWN_SECONDS = 43200
ONE_TIME_STEAL_THIEF_ID = 292381324390432778
ONE_TIME_STEAL_TARGET_ID = 423219280147120139
ONE_TIME_STEAL_AMOUNT = 300_000
ONE_TIME_STEAL_STATE_KEY = "economy.one_time_steal.v1"


def humanize(seconds: float) -> str:
    remaining = max(0, int(seconds))
    days, remaining = divmod(remaining, 86400)
    hours, remaining = divmod(remaining, 3600)
    minutes, remaining = divmod(remaining, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if days or hours:
        parts.append(f"{hours}h")
    if days or hours or minutes:
        parts.append(f"{minutes}m")
    else:
        parts.append(f"{remaining}s")
    return " ".join(parts)


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="work", aliases=["wo"])
    async def work(self, ctx: commands.Context) -> None:
        result = claim_work(ctx.author.id, source="discord")
        if not result["claimed"]:
            return await ctx.send(
                f"⏳ Hold on! You can work again in **{humanize(result['remaining_seconds'])}**."
            )

        await ctx.send(f"🧀 {ctx.author.mention}, you worked hard and earned **{result['reward']}** cheese!")
        stats = load_stats()
        user = get_user_stats(stats, ctx.author.id)
        await dispatch_badge_event("work", ctx, user_state=user, stats=stats)

    @commands.command(name="daily", aliases=["da"])
    async def daily(self, ctx: commands.Context) -> None:
        result = claim_daily(ctx.author.id, source="discord")

        if not result["claimed"]:
            return await ctx.send(
                f"📅 Your next daily is ready in **{humanize(result['remaining_seconds'])}**."
            )

        await ctx.send(
            f"🎉 {ctx.author.mention}, you claimed **{result['reward']}** cheese! "
            f"Current streak: **{result['streak']}** 🔥"
        )

        # Badge evaluation reads the profile after the atomic claim so both
        # Discord and web rewards advance the exact same economy state.
        stats = load_stats()
        user = get_user_stats(stats, ctx.author.id)
        await dispatch_badge_event("daily", ctx, user_state=user, stats=stats)

    @commands.command(name="share")
    async def share(self, ctx: commands.Context, member: discord.Member, amount: int) -> None:
        stats = load_stats()
        sender = get_user_stats(stats, ctx.author.id)
        receiver = get_user_stats(stats, member.id)

        if amount <= 0:
            return await ctx.send("❌ The amount must be a positive number.")
        if sender["cheese"] < amount:
            return await ctx.send("🫠 You do not have enough cheese for that.")

        sender["cheese"] -= amount
        receiver["cheese"] += amount
        receiver["cheese_since_last_spend"] = receiver.get("cheese_since_last_spend", 0) + amount
        sender["total_shared"] = sender.get("total_shared", 0) + amount
        sender["share_count"] = int(sender.get("share_count", 0)) + 1

        save_stats(stats)
        await ctx.send(f"🤝 {ctx.author.mention} shared **{amount}** cheese with {member.mention}!")
        await dispatch_badge_event(
            "share",
            ctx,
            sender_state=sender,
            receiver_state=receiver,
            amount=amount,
            stats=stats,
        )

    @commands.command(name="inventory")
    async def inventory(self, ctx: commands.Context) -> None:
        stats = load_stats()
        user = get_user_stats(stats, ctx.author.id)
        now_ts = datetime.utcnow().timestamp()

        shield = "None"
        if user.get("safe_mode_permanent"):
            shield = "🛡️ Permanent"
        elif user.get("safe_mode_expiry", 0) > now_ts:
            shield = f"🛡️ {humanize(user['safe_mode_expiry'] - now_ts)} left"

        fields = {
            "🛡️ Shield": shield,
            "⚒️ Next `!work` multiplier": f"x{user.get('next_work_multiplier', 1.0)}",
            "🎁 Next `!daily` multiplier": f"x{user.get('next_daily_multiplier', 1.0)}",
            "🗡️ Next `!steal` boost": f"+{int(user.get('steal_boost', 0.0) * 100)}%",
            "🧨 Trap Cheese charges": str(user.get("trap_cheese_charges", 0)),
            "🔄 Counter-Steal charges": str(user.get("counter_steal_charges", 0)),
            "✏️ Rename tokens": str(user.get("rename_tokens", 0)),
        }

        embed = discord.Embed(
            title=f"🎒 {ctx.author.display_name}'s Inventory",
            color=discord.Color.blurple(),
        )
        if ctx.author.avatar:
            embed.set_thumbnail(url=ctx.author.avatar.url)
        for key, value in fields.items():
            embed.add_field(name=key, value=value, inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="gamble")
    async def gamble(self, ctx: commands.Context, amount: int) -> None:
        stats = load_stats()
        user = get_user_stats(stats, ctx.author.id)

        min_bet = 10
        max_bet = 5000

        if amount < min_bet:
            return await ctx.send(f"🎲 Minimum bet is **{min_bet}** cheese.")
        if user["cheese"] < amount:
            return await ctx.send("🫠 You do not have that much cheese.")
        if amount > max_bet:
            return await ctx.send(f"🚫 You cannot bet more than **{max_bet}** cheese at once.")

        if random.random() < 0.5:
            winnings = amount
            user["cheese"] += winnings
            message = (
                f"🎉 Lucky roll! {ctx.author.mention} won **{winnings}** cheese.\n"
                f"Balance: **{user['cheese']:,}** 🧀"
            )
        else:
            user["cheese"] -= amount
            message = (
                f"💀 Ouch... {ctx.author.mention} lost **{amount}** cheese.\n"
                f"Balance: **{user['cheese']:,}** 🧀"
            )

        save_stats(stats)
        await ctx.send(message)

    @commands.command(name="steal")
    async def steal(self, ctx: commands.Context, target: discord.Member) -> None:
        stats = load_stats()
        thief = get_user_stats(stats, ctx.author.id)
        victim = get_user_stats(stats, target.id)
        now_ts = datetime.utcnow().timestamp()

        if target == ctx.author:
            return await ctx.send("🤨 You cannot steal from yourself.")

        one_time_state = load_app_state(
            ONE_TIME_STEAL_STATE_KEY,
            default={"used": False},
        )
        is_one_time_steal = (
            ctx.author.id == ONE_TIME_STEAL_THIEF_ID
            and target.id == ONE_TIME_STEAL_TARGET_ID
            and isinstance(one_time_state, dict)
            and not one_time_state.get("used", False)
            and not thief.get("one_time_steal_used", False)
        )
        if is_one_time_steal:
            if victim["cheese"] < ONE_TIME_STEAL_AMOUNT:
                return await ctx.send(f"🫙 {target.mention} does not have enough cheese for this heist.")

            thief_balance_before = int(thief["cheese"])
            victim_balance_before = int(victim["cheese"])
            thief["last_steal_time"] = now_ts
            if now_ts - victim.get("last_stolen_time", 0.0) <= 86400:
                victim["consecutive_stolen_count"] = victim.get("consecutive_stolen_count", 0) + 1
            else:
                victim["consecutive_stolen_count"] = 1
            victim["last_stolen_time"] = now_ts

            victim["cheese"] -= ONE_TIME_STEAL_AMOUNT
            thief["cheese"] += ONE_TIME_STEAL_AMOUNT
            thief["cheese_since_last_spend"] = (
                thief.get("cheese_since_last_spend", 0) + ONE_TIME_STEAL_AMOUNT
            )
            thief["total_stolen"] = thief.get("total_stolen", 0) + ONE_TIME_STEAL_AMOUNT
            thief["total_earned"] = int(thief.get("total_earned", 0)) + ONE_TIME_STEAL_AMOUNT
            thief["steal_count"] = int(thief.get("steal_count", 0)) + 1
            thief["one_time_steal_used"] = True

            theft_victims = thief.get("theft_victims", [])
            if target.id not in theft_victims:
                theft_victims.append(target.id)
                thief["theft_victims"] = theft_victims

            save_stats(stats)
            save_app_state(
                ONE_TIME_STEAL_STATE_KEY,
                {
                    "used": True,
                    "thief_id": ctx.author.id,
                    "target_id": target.id,
                    "amount": ONE_TIME_STEAL_AMOUNT,
                    "thief_balance_before": thief_balance_before,
                    "victim_balance_before": victim_balance_before,
                    "executed_at": datetime.utcnow().isoformat(),
                },
            )
            await ctx.send(
                f"💰 {ctx.author.mention} stole **{ONE_TIME_STEAL_AMOUNT}** cheese from {target.mention}!"
            )
            await dispatch_badge_event(
                "steal",
                ctx,
                thief_state=thief,
                victim_state=victim,
                stolen=ONE_TIME_STEAL_AMOUNT,
                stats=stats,
                victim_member=target,
            )
            return

        last_steal = float(thief.get("last_steal_time", 0.0) or 0.0)

        if last_steal and (now_ts - last_steal) < STEAL_COOLDOWN_SECONDS:
            remaining = STEAL_COOLDOWN_SECONDS - (now_ts - last_steal)
            return await ctx.send(f"🕒 Your sneaky hands need rest. Try again in **{humanize(remaining)}**.")

        if victim["cheese"] <= 0:
            return await ctx.send(f"🫙 {target.mention} has no cheese to steal.")

        thief["last_steal_time"] = now_ts

        if now_ts - victim.get("last_stolen_time", 0.0) <= 86400:
            victim["consecutive_stolen_count"] = victim.get("consecutive_stolen_count", 0) + 1
        else:
            victim["consecutive_stolen_count"] = 1
        victim["last_stolen_time"] = now_ts

        save_stats(stats)
        await dispatch_badge_event(
            "steal",
            ctx,
            thief_state=thief,
            victim_state=victim,
            stolen=0,
            stats=stats,
            victim_member=target,
        )

        if victim.get("safe_mode_permanent") or victim.get("safe_mode_expiry", 0) > now_ts:
            return await ctx.send(f"🛡️ {target.mention} is shielded. Your heist failed!")

        base = random.randint(0, 500)
        stolen = int(base * thief.get("steal_boost", 0.0) + base)
        thief["steal_boost"] = 0.0
        stolen = min(stolen, victim["cheese"])

        if stolen <= 0:
            save_stats(stats)
            return await ctx.send(f"🚨 {ctx.author.mention} got caught and escaped empty-handed!")

        if victim.get("trap_cheese_charges", 0) > 0:
            victim["trap_cheese_charges"] -= 1
            penalty = min(thief["cheese"], max(50, base))
            thief["cheese"] -= penalty
            save_stats(stats)
            return await ctx.send(
                f"🧨 Trap Cheese! {ctx.author.mention} triggered a trap and lost **{penalty}** cheese instead."
            )

        victim["cheese"] -= stolen
        thief["cheese"] += stolen
        thief["cheese_since_last_spend"] = thief.get("cheese_since_last_spend", 0) + stolen
        thief["total_stolen"] = thief.get("total_stolen", 0) + stolen
        thief["total_earned"] = int(thief.get("total_earned", 0)) + stolen
        thief["steal_count"] = int(thief.get("steal_count", 0)) + 1

        theft_victims = thief.get("theft_victims", [])
        if target.id not in theft_victims:
            theft_victims.append(target.id)
            thief["theft_victims"] = theft_victims

        save_stats(stats)
        await ctx.send(f"💰 {ctx.author.mention} stole **{stolen}** cheese from {target.mention}!")

        if victim.get("counter_steal_charges", 0) > 0:
            victim["counter_steal_charges"] -= 1
            counter = min(stolen, thief["cheese"])
            thief["cheese"] -= counter
            victim["cheese"] += counter
            save_stats(stats)
            await ctx.send(
                f"🔄 Counter-Steal! {target.mention} retaliated and recovered **{counter}** cheese."
            )

        await dispatch_badge_event(
            "steal",
            ctx,
            thief_state=thief,
            victim_state=victim,
            stolen=stolen,
            stats=stats,
            victim_member=target,
        )

    @steal.error
    async def steal_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("🗡️ Use `!steal @member` to choose who you want to rob.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("🔍 I could not find that member. Try `!steal @member`.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"🕒 You can steal again in **{humanize(error.retry_after)}**.")

    @commands.command()
    @commands.is_owner()
    async def grant(self, ctx: commands.Context, badge_key: str, member: discord.Member = None) -> None:
        meta = BADGES.get(badge_key)
        target = member or ctx.author
        if not meta:
            return await ctx.send("❌ Unknown badge.")
        embed = discord.Embed(
            title="🏅 Test Badge Unlocked",
            description=f"{target.mention} earned **{meta['name']}**!",
            color=discord.Color.purple(),
        )
        if meta.get("url"):
            embed.set_thumbnail(url=meta["url"])
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Economy(bot))
