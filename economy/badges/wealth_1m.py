from .base import Badge

WEALTH_1M = Badge(
    key="wealth_1m",
    name="Millionaire",
    url="https://i.imgur.com/wealth1m.png",
    description="Reach 1,000,000 cheese."
)

class _Wealth1M(Badge):
    def on_work(self, ctx, user_state, stats) -> bool:
        if user_state.get("cheese", 0) >= 1_000_000:
            return self.award(ctx.author.id)
        return False
    def on_daily(self, ctx, user_state, stats) -> bool:
        return self.on_work(ctx, user_state, stats)

WEALTH_1M.__class__ = _Wealth1M
