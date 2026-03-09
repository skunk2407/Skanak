import os

import discord

from .base import grant_badge
from .catalog import BADGES as CATALOG
from .share_progression import SHARE_BRONZE, SHARE_DIAMAND, SHARE_GOLD, SHARE_RED, SHARE_SILVER
from .work_progression import WORK_BRONZE, WORK_DIAMAND, WORK_GOLD, WORK_RED, WORK_SILVER

REGISTRY = {
    WORK_BRONZE.key: WORK_BRONZE,
    WORK_SILVER.key: WORK_SILVER,
    WORK_GOLD.key: WORK_GOLD,
    WORK_DIAMAND.key: WORK_DIAMAND,
    WORK_RED.key: WORK_RED,
    SHARE_BRONZE.key: SHARE_BRONZE,
    SHARE_SILVER.key: SHARE_SILVER,
    SHARE_GOLD.key: SHARE_GOLD,
    SHARE_DIAMAND.key: SHARE_DIAMAND,
    SHARE_RED.key: SHARE_RED,
}

BADGES = CATALOG


def _clean_badges(user_state: dict) -> bool:
    badges = user_state.setdefault("badges", [])
    if "work_diamond" in badges and "work_diamand" not in badges:
        badges = ["work_diamand" if key == "work_diamond" else key for key in badges]
        user_state["badges"] = badges
    if "share_diamond" in badges and "share_diamand" not in badges:
        badges = ["share_diamand" if key == "share_diamond" else key for key in badges]
        user_state["badges"] = badges

    cleaned = []
    seen = set()
    for key in badges:
        if key in BADGES and key not in seen:
            cleaned.append(key)
            seen.add(key)

    work_keys = ["work_bronze", "work_silver", "work_gold", "work_diamand", "work_red"]
    highest_work = None
    for key in work_keys:
        if key in cleaned:
            highest_work = key
    if highest_work:
        cleaned = [key for key in cleaned if key not in work_keys]
        cleaned.append(highest_work)

    share_keys = ["share_bronze", "share_silver", "share_gold", "share_diamand", "share_red"]
    highest_share = None
    for key in share_keys:
        if key in cleaned:
            highest_share = key
    if highest_share:
        cleaned = [key for key in cleaned if key not in share_keys]
        cleaned.append(highest_share)

    changed = cleaned != badges
    if changed:
        user_state["badges"] = cleaned
    return changed


# --- API publique ---
def award_badge(user_id: int, key: str) -> bool:
    if key not in BADGES:
        return False
    b = REGISTRY.get(key)
    return b.award(user_id) if b else grant_badge(user_id, key)


async def dispatch_badge_event(event: str, ctx, **kwargs):
    """Dispatch badge events and post unlock embeds when a new badge is earned."""
    stats = kwargs.get("stats")
    states = [
        kwargs.get("user_state"),
        kwargs.get("sender_state"),
        kwargs.get("receiver_state"),
    ]
    dirty = False
    for state in states:
        if isinstance(state, dict) and _clean_badges(state):
            dirty = True
    if dirty:
        from economy.stats import save_stats

        save_stats(stats)

    triggered = []
    for badge in REGISTRY.values():
        try:
            if badge.on_event(event, ctx, **kwargs):
                triggered.append(badge)
        except Exception as exc:
            print(f"[Badge {badge.key}] Error in on_event: {exc}")

    for badge in triggered:
        target = ctx.author
        embed = badge.build_embed(target)
        if not embed:
            continue

        image_path = os.path.join(os.path.dirname(__file__), "images", "work", f"{badge.key}.png")
        if os.path.isfile(image_path):
            filename = f"{badge.key}.png"
            embed.set_thumbnail(url=f"attachment://{filename}")
            await ctx.send(embed=embed, file=discord.File(image_path, filename=filename))
        else:
            await ctx.send(embed=embed)
