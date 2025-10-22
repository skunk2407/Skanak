from .base import Badge

STREAK_30 = Badge(
    key="streak_30",
    name="Monthly Grinder",
    url="https://i.imgur.com/streak30.png",
    description="Reach 30 daily streak."
)

class _Streak30(Badge):
    def on_daily(self, ctx, user_state, stats) -> bool:
        if user_state.get("daily_streak", 0) == 30:
            return self.award(ctx.author.id)
        return False

STREAK_30.__class__ = _Streak30
