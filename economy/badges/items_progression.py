from economy.stats import save_stats

from .base import Badge

ITEM_TIERS = [
    ("item_bronze", 1),
    ("item_silver", 25),
    ("item_gold", 50),
    ("item_diamand", 75),
    ("item_red", 100),
]


class ItemTierBadge(Badge):
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

    def on_shop(self, ctx, user_state: dict, stats: dict) -> bool:
        purchase_count = int(user_state.get("shop_purchases", 0))
        if purchase_count < self.threshold:
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


ITEM_BRONZE = ItemTierBadge(
    key="item_bronze",
    name="Item Bronze",
    description="Purchased 1 shop item.",
    threshold=1,
    replaces=[],
    blocked_by=["item_silver", "item_gold", "item_diamand", "item_red"],
)

ITEM_SILVER = ItemTierBadge(
    key="item_silver",
    name="Item Silver",
    description="Purchased 25 shop items.",
    threshold=25,
    replaces=["item_bronze"],
    blocked_by=["item_gold", "item_diamand", "item_red"],
)

ITEM_GOLD = ItemTierBadge(
    key="item_gold",
    name="Item Gold",
    description="Purchased 50 shop items.",
    threshold=50,
    replaces=["item_bronze", "item_silver"],
    blocked_by=["item_diamand", "item_red"],
)

ITEM_DIAMAND = ItemTierBadge(
    key="item_diamand",
    name="Item Diamand",
    description="Purchased 75 shop items.",
    threshold=75,
    replaces=["item_bronze", "item_silver", "item_gold"],
    blocked_by=["item_red"],
)

ITEM_RED = ItemTierBadge(
    key="item_red",
    name="Item Rouge",
    description="Purchased 100 shop items.",
    threshold=100,
    replaces=["item_bronze", "item_silver", "item_gold", "item_diamand"],
    blocked_by=[],
)
