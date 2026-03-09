from economy.stats import save_stats

from .base import Badge

WORK_TIERS = [
    ("work_bronze", 1),
    ("work_silver", 25),
    ("work_gold", 50),
    ("work_diamond", 100),
]


class WorkTierBadge(Badge):
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

    def on_work(self, ctx, user_state, stats) -> bool:
        work_count = int(user_state.get("work_count", 0))
        if work_count < self.threshold:
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


WORK_BRONZE = WorkTierBadge(
    key="work_bronze",
    name="Work Bronze",
    description="Used `!work` for the first time.",
    threshold=1,
    replaces=[],
    blocked_by=["work_silver", "work_gold", "work_diamond"],
)

WORK_SILVER = WorkTierBadge(
    key="work_silver",
    name="Work Silver",
    description="Reached 25 uses of `!work`.",
    threshold=25,
    replaces=["work_bronze"],
    blocked_by=["work_gold", "work_diamond"],
)

WORK_GOLD = WorkTierBadge(
    key="work_gold",
    name="Work Gold",
    description="Reached 50 uses of `!work`.",
    threshold=50,
    replaces=["work_bronze", "work_silver"],
    blocked_by=["work_diamond"],
)

WORK_DIAMOND = WorkTierBadge(
    key="work_diamond",
    name="Work Diamond",
    description="Reached 100 uses of `!work`.",
    threshold=100,
    replaces=["work_bronze", "work_silver", "work_gold"],
    blocked_by=[],
)
