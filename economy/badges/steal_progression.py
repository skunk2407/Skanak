from economy.stats import save_stats

from .base import Badge

STEAL_TIERS = [
    ("steal_bronze", 1),
    ("steal_silver", 25),
    ("steal_gold", 50),
    ("steal_diamand", 75),
    ("steal_red", 100),
]


class StealTierBadge(Badge):
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

    def on_steal(self, ctx, thief_state: dict, victim_state: dict, stolen: int, stats: dict) -> bool:
        if int(stolen or 0) <= 0:
            return False

        steal_count = int(thief_state.get("steal_count", 0))
        if steal_count < self.threshold:
            return False

        badges = thief_state.setdefault("badges", [])
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


STEAL_BRONZE = StealTierBadge(
    key="steal_bronze",
    name="Steal Bronze",
    description="Use `!steal` successfully 1 time.",
    threshold=1,
    replaces=[],
    blocked_by=["steal_silver", "steal_gold", "steal_diamand", "steal_red"],
)

STEAL_SILVER = StealTierBadge(
    key="steal_silver",
    name="Steal Silver",
    description="Use `!steal` successfully 25 times.",
    threshold=25,
    replaces=["steal_bronze"],
    blocked_by=["steal_gold", "steal_diamand", "steal_red"],
)

STEAL_GOLD = StealTierBadge(
    key="steal_gold",
    name="Steal Gold",
    description="Use `!steal` successfully 50 times.",
    threshold=50,
    replaces=["steal_bronze", "steal_silver"],
    blocked_by=["steal_diamand", "steal_red"],
)

STEAL_DIAMAND = StealTierBadge(
    key="steal_diamand",
    name="Steal Diamand",
    description="Use `!steal` successfully 75 times.",
    threshold=75,
    replaces=["steal_bronze", "steal_silver", "steal_gold"],
    blocked_by=["steal_red"],
)

STEAL_RED = StealTierBadge(
    key="steal_red",
    name="Steal Rouge",
    description="Use `!steal` successfully 100 times.",
    threshold=100,
    replaces=["steal_bronze", "steal_silver", "steal_gold", "steal_diamand"],
    blocked_by=[],
)
