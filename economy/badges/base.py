# base.py
from dataclasses import dataclass

import discord

from economy.stats import load_stats, save_stats


def _load_stats():
    return load_stats()


def _save_stats(stats: dict):
    save_stats(stats)


def _ensure_user(stats: dict, uid: int):
    suid = str(uid)
    if suid not in stats:
        stats[suid] = {"badges": []}
    stats[suid].setdefault("badges", [])
    return stats[suid]


def grant_badge(user_id: int, key: str) -> bool:
    """Add a badge to a user if missing. Return True when newly granted."""
    stats = _load_stats()
    user = _ensure_user(stats, user_id)
    if key not in user["badges"]:
        user["badges"].append(key)
        _save_stats(stats)
        return True
    return False


@dataclass
class Badge:
    key: str
    name: str
    url: str
    description: str = ""

    # Event hooks (True if the badge was newly awarded)
    def on_work(self, ctx, user_state: dict, stats: dict) -> bool:
        return False

    def on_daily(self, ctx, user_state: dict, stats: dict) -> bool:
        return False

    def on_share(self, ctx, sender_state: dict, receiver_state: dict, amount: int, stats: dict) -> bool:
        return False

    def on_steal(self, ctx, thief_state: dict, victim_state: dict, stolen: int, stats: dict) -> bool:
        return False

    def award(self, user_id: int) -> bool:
        return grant_badge(user_id, self.key)

    def build_embed(self, user: discord.abc.User):
        if not user:
            return None
        embed = discord.Embed(
            title="🎉 New Badge Unlocked!",
            description=f"{user.mention} earned **{self.name}**!",
            color=discord.Color.gold(),
        )
        if self.description:
            embed.add_field(name="How it was unlocked", value=self.description, inline=False)
        if self.url:
            embed.set_thumbnail(url=self.url)
        return embed

    # Generic router called by the dispatcher
    def on_event(self, event: str, ctx=None, **kwargs) -> bool:
        stats = kwargs.get("stats")
        if event == "work":
            return self.on_work(ctx, kwargs.get("user_state", {}), stats)
        if event == "daily":
            return self.on_daily(ctx, kwargs.get("user_state", {}), stats)
        if event == "share":
            return self.on_share(
                ctx,
                kwargs.get("sender_state", {}),
                kwargs.get("receiver_state", {}),
                kwargs.get("amount", 0),
                stats,
            )
        if event == "steal":
            return self.on_steal(
                ctx,
                kwargs.get("thief_state", {}),
                kwargs.get("victim_state", {}),
                kwargs.get("stolen", 0),
                stats,
            )
        return False
