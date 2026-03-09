from economy.stats import save_stats

from .base import Badge

SHARE_TIERS = [
    ("share_bronze", 1),
    ("share_silver", 25),
    ("share_gold", 50),
    ("share_diamand", 75),
    ("share_red", 100),
]


class ShareTierBadge(Badge):
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

    def on_share(self, ctx, sender_state: dict, receiver_state: dict, amount: int, stats: dict) -> bool:
        share_count = int(sender_state.get("share_count", 0))
        if share_count < self.threshold:
            return False

        badges = sender_state.setdefault("badges", [])
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


SHARE_BRONZE = ShareTierBadge(
    key="share_bronze",
    name="Share Bronze",
    description="Used `!share` for the first time.",
    threshold=1,
    replaces=[],
    blocked_by=["share_silver", "share_gold", "share_diamand", "share_red"],
)

SHARE_SILVER = ShareTierBadge(
    key="share_silver",
    name="Share Silver",
    description="Reached 25 uses of `!share`.",
    threshold=25,
    replaces=["share_bronze"],
    blocked_by=["share_gold", "share_diamand", "share_red"],
)

SHARE_GOLD = ShareTierBadge(
    key="share_gold",
    name="Share Gold",
    description="Reached 50 uses of `!share`.",
    threshold=50,
    replaces=["share_bronze", "share_silver"],
    blocked_by=["share_diamand", "share_red"],
)

SHARE_DIAMAND = ShareTierBadge(
    key="share_diamand",
    name="Share Diamand",
    description="Reached 75 uses of `!share`.",
    threshold=75,
    replaces=["share_bronze", "share_silver", "share_gold"],
    blocked_by=["share_red"],
)

SHARE_RED = ShareTierBadge(
    key="share_red",
    name="Share Rouge",
    description="Reached 100 uses of `!share`.",
    threshold=100,
    replaces=["share_bronze", "share_silver", "share_gold", "share_diamand"],
    blocked_by=[],
)
