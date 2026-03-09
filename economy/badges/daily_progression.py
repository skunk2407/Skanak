from economy.stats import save_stats

from .base import Badge

DAILY_TIERS = [
    ("daily_bronze", 1),
    ("daily_silver", 25),
    ("daily_gold", 50),
    ("daily_diamand", 75),
    ("daily_red", 100),
]


class DailyTierBadge(Badge):
    def __init__(
        self,
        key: str,
        name: str,
        description: str,
        threshold: int,
        replaces: list[str],
        blocked_by: list[str],
    ):
        super().__init__(key=key, name=name, url="", description=description)
        self.threshold = threshold
        self.replaces = replaces
        self.blocked_by = blocked_by

    def on_daily(self, ctx, user_state: dict, stats: dict) -> bool:
        daily_count = int(user_state.get("daily_count", 0))
        if daily_count < self.threshold:
            return False

        badges = user_state.setdefault("badges", [])
        for key in self.blocked_by:
            if key in badges:
                return False

        changed = False
        for key in self.replaces:
            if key in badges:
                badges.remove(key)
                changed = True

        newly_awarded = False
        if self.key not in badges:
            badges.append(self.key)
            newly_awarded = True
            changed = True

        if changed:
            save_stats(stats)
        return newly_awarded


DAILY_BRONZE = DailyTierBadge(
    key="daily_bronze",
    name="Daily Bronze",
    description="Used `!daily` for the first time.",
    threshold=1,
    replaces=[],
    blocked_by=["daily_silver", "daily_gold", "daily_diamand", "daily_red"],
)

DAILY_SILVER = DailyTierBadge(
    key="daily_silver",
    name="Daily Silver",
    description="Reached 25 uses of `!daily`.",
    threshold=25,
    replaces=["daily_bronze"],
    blocked_by=["daily_gold", "daily_diamand", "daily_red"],
)

DAILY_GOLD = DailyTierBadge(
    key="daily_gold",
    name="Daily Gold",
    description="Reached 50 uses of `!daily`.",
    threshold=50,
    replaces=["daily_bronze", "daily_silver"],
    blocked_by=["daily_diamand", "daily_red"],
)

DAILY_DIAMAND = DailyTierBadge(
    key="daily_diamand",
    name="Daily Diamand",
    description="Reached 75 uses of `!daily`.",
    threshold=75,
    replaces=["daily_bronze", "daily_silver", "daily_gold"],
    blocked_by=["daily_red"],
)

DAILY_RED = DailyTierBadge(
    key="daily_red",
    name="Daily Rouge",
    description="Reached 100 uses of `!daily`.",
    threshold=100,
    replaces=["daily_bronze", "daily_silver", "daily_gold", "daily_diamand"],
    blocked_by=[],
)
