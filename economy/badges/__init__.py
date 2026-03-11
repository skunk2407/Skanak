import os

import discord

from .base import grant_badge
from .catalog import BADGES as CATALOG
from .daily_progression import DAILY_BRONZE, DAILY_DIAMAND, DAILY_GOLD, DAILY_RED, DAILY_SILVER
from .earned_progression import EARNED_BLUE, EARNED_BRONZE, EARNED_GOLD, EARNED_RED, EARNED_SILVER
from .items_progression import ITEM_BRONZE, ITEM_DIAMAND, ITEM_GOLD, ITEM_RED, ITEM_SILVER
from .share_progression import SHARE_BRONZE, SHARE_DIAMAND, SHARE_GOLD, SHARE_RED, SHARE_SILVER
from .steal_progression import STEAL_BRONZE, STEAL_DIAMAND, STEAL_GOLD, STEAL_RED, STEAL_SILVER
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
    DAILY_BRONZE.key: DAILY_BRONZE,
    DAILY_SILVER.key: DAILY_SILVER,
    DAILY_GOLD.key: DAILY_GOLD,
    DAILY_DIAMAND.key: DAILY_DIAMAND,
    DAILY_RED.key: DAILY_RED,
    ITEM_BRONZE.key: ITEM_BRONZE,
    ITEM_SILVER.key: ITEM_SILVER,
    ITEM_GOLD.key: ITEM_GOLD,
    ITEM_DIAMAND.key: ITEM_DIAMAND,
    ITEM_RED.key: ITEM_RED,
    STEAL_BRONZE.key: STEAL_BRONZE,
    STEAL_SILVER.key: STEAL_SILVER,
    STEAL_GOLD.key: STEAL_GOLD,
    STEAL_DIAMAND.key: STEAL_DIAMAND,
    STEAL_RED.key: STEAL_RED,
    EARNED_BRONZE.key: EARNED_BRONZE,
    EARNED_SILVER.key: EARNED_SILVER,
    EARNED_GOLD.key: EARNED_GOLD,
    EARNED_BLUE.key: EARNED_BLUE,
    EARNED_RED.key: EARNED_RED,
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
    if "daily_diamond" in badges and "daily_diamand" not in badges:
        badges = ["daily_diamand" if key == "daily_diamond" else key for key in badges]
        user_state["badges"] = badges
    if "item_diamond" in badges and "item_diamand" not in badges:
        badges = ["item_diamand" if key == "item_diamond" else key for key in badges]
        user_state["badges"] = badges
    if "steal_diamond" in badges and "steal_diamand" not in badges:
        badges = ["steal_diamand" if key == "steal_diamond" else key for key in badges]
        user_state["badges"] = badges
    if "certified" in badges and "cheese_certified" not in badges:
        badges = ["cheese_certified" if key == "certified" else key for key in badges]
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

    daily_keys = ["daily_bronze", "daily_silver", "daily_gold", "daily_diamand", "daily_red"]
    highest_daily = None
    for key in daily_keys:
        if key in cleaned:
            highest_daily = key
    if highest_daily:
        cleaned = [key for key in cleaned if key not in daily_keys]
        cleaned.append(highest_daily)

    item_keys = ["item_bronze", "item_silver", "item_gold", "item_diamand", "item_red"]
    highest_item = None
    for key in item_keys:
        if key in cleaned:
            highest_item = key
    if highest_item:
        cleaned = [key for key in cleaned if key not in item_keys]
        cleaned.append(highest_item)

    steal_keys = ["steal_bronze", "steal_silver", "steal_gold", "steal_diamand", "steal_red"]
    highest_steal = None
    for key in steal_keys:
        if key in cleaned:
            highest_steal = key
    if highest_steal:
        cleaned = [key for key in cleaned if key not in steal_keys]
        cleaned.append(highest_steal)

    earned_keys = ["earned_bronze", "earned_silver", "earned_gold", "earned_blue", "earned_red"]
    highest_earned = None
    for key in earned_keys:
        if key in cleaned:
            highest_earned = key
    if highest_earned:
        cleaned = [key for key in cleaned if key not in earned_keys]
        cleaned.append(highest_earned)

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

        image_path = os.path.join(os.path.dirname(__file__), "images", "badges_logo", f"{badge.key}.png")
        if os.path.isfile(image_path):
            filename = f"{badge.key}.png"
            embed.set_thumbnail(url=f"attachment://{filename}")
            await ctx.send(embed=embed, file=discord.File(image_path, filename=filename))
        else:
            await ctx.send(embed=embed)
