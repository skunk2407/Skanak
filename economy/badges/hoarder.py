from .base import Badge, grant_badge

HOARDER = Badge(
    key="hoarder",
    name="Hoarder",
    url="https://i.imgur.com/hoarder.png",
    description="Accumulate 150,000 cheese without spending."
)

class _Hoarder(Badge):
    def on_work(self, ctx, user_state, stats) -> bool:
        if user_state.get("cheese_since_last_spend", 0) >= 150_000:
            return self.award(ctx.author.id)
        return False
    def on_daily(self, ctx, user_state, stats) -> bool:
        return self.on_work(ctx, user_state, stats)

# Remplace l’instance simple par la version avec logique
HOARDER.__class__ = _Hoarder
