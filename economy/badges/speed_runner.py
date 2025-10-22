from .base import Badge

SPEED_RUNNER = Badge(
    key="speed_runner",
    name="Speed Runner",
    url="https://i.imgur.com/speedrunner.png",
    description="Do 10 quick combos within 60s between daily→work."
)

class _SpeedRunner(Badge):
    def on_work(self, ctx, user_state, stats) -> bool:
        if user_state.get("quick_combo", 0) >= 10:
            return self.award(ctx.author.id)
        return False

SPEED_RUNNER.__class__ = _SpeedRunner
