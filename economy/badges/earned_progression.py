from economy.stats import save_stats

from .base import Badge

EARNED_TIERS = [
    ("earned_bronze", 10000),
    ("earned_silver", 50000),
    ("earned_gold", 100000),
    ("earned_blue", 250000),
    ("earned_red", 750000),
]


class EarnedTierBadge(Badge):
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

    def _check_award(self, user_state: dict, stats: dict) -> bool:
        total_earned = int(user_state.get("total_earned", 0))
        if total_earned < self.threshold:
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

    def on_work(self, ctx, user_state: dict, stats: dict) -> bool:
        return self._check_award(user_state, stats)

    def on_daily(self, ctx, user_state: dict, stats: dict) -> bool:
        return self._check_award(user_state, stats)

    def on_steal(self, ctx, thief_state: dict, victim_state: dict, stolen: int, stats: dict) -> bool:
        if int(stolen or 0) <= 0:
            return False
        return self._check_award(thief_state, stats)


EARNED_BRONZE = EarnedTierBadge(
    key="earned_bronze",
    name="Total Cheese Bronze",
    description="Reach 10000 total cheese earned.",
    threshold=10000,
    replaces=[],
    blocked_by=["earned_silver", "earned_gold", "earned_blue", "earned_red"],
)

EARNED_SILVER = EarnedTierBadge(
    key="earned_silver",
    name="Total Cheese Silver",
    description="Reach 50000 total cheese earned.",
    threshold=50000,
    replaces=["earned_bronze"],
    blocked_by=["earned_gold", "earned_blue", "earned_red"],
)

EARNED_GOLD = EarnedTierBadge(
    key="earned_gold",
    name="Total Cheese Gold",
    description="Reach 100000 total cheese earned.",
    threshold=100000,
    replaces=["earned_bronze", "earned_silver"],
    blocked_by=["earned_blue", "earned_red"],
)

EARNED_BLUE = EarnedTierBadge(
    key="earned_blue",
    name="Total Cheese Blue",
    description="Reach 250000 total cheese earned.",
    threshold=250000,
    replaces=["earned_bronze", "earned_silver", "earned_gold"],
    blocked_by=["earned_red"],
)

EARNED_RED = EarnedTierBadge(
    key="earned_red",
    name="Total Cheese Rouge",
    description="Reach 750000 total cheese earned.",
    threshold=750000,
    replaces=["earned_bronze", "earned_silver", "earned_gold", "earned_blue"],
    blocked_by=[],
)
