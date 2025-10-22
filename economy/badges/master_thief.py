from .base import Badge

MASTER_THIEF = Badge(
    key="master_thief",
    name="Master Thief",
    url="https://i.imgur.com/masterthief.png",
    description="Steal from 50 unique victims."
)

class _MasterThief(Badge):
    def on_steal(self, ctx, thief_state, victim_state, stolen, stats):
        if len(thief_state.get("theft_victims", [])) >= 50:
            if self.award(ctx.author.id):
                return "thief"
        return False

MASTER_THIEF.__class__ = _MasterThief
