from .base import Badge

STREAK_7 = Badge(
    key="streak_7",
    name="Weekly Warrior",
    url="https://i.imgur.com/streak7.png",
    description="Reach 7 daily streak."
)

class _Streak7(Badge):
    def on_daily(self, ctx, user_state, stats) -> bool:
        if user_state.get("daily_streak", 0) == 7:
            return self.award(ctx.author.id)
        return False

STREAK_7.__class__ = _Streak7
