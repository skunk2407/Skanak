from .base import Badge

UNDERDOG = Badge(
    key="underdog",
    name="Underdog",
    url="https://i.imgur.com/underdog.png",
    description="Total stolen > total earned."
)

class _Underdog(Badge):
    def on_steal(self, ctx, thief_state, victim_state, stolen, stats):
        if thief_state.get("total_stolen", 0) > thief_state.get("total_earned", 0):
            if self.award(ctx.author.id):
                return "thief"
        return False

UNDERDOG.__class__ = _Underdog
