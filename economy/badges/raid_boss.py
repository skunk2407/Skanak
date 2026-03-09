from .base import Badge

RAID_BOSS = Badge(
    key="raid_boss",
    name="Raid Boss",
    url="https://i.imgur.com/raidboss.png",
    description="Get stolen from 10 times within 24h."
)

class _RaidBoss(Badge):
    # Ici c'est la victime qui gagne le badge
    def on_steal(self, ctx, thief_state, victim_state, stolen, stats):
        if victim_state.get("consecutive_stolen_count", 0) >= 10:
            victim_id = ctx.message.mentions[0].id if ctx.message.mentions else None
            if victim_id is not None:
                return self.award(victim_id)
        return False

RAID_BOSS.__class__ = _RaidBoss
