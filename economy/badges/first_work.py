from .base import Badge

FIRST_WORK = Badge(
    key="first_work",
    name="First Work",
    url="https://i.imgur.com/firstwork.png",
    description="Use !work for the first time."
)

class _FirstWork(Badge):
    def on_work(self, ctx, user_state, stats) -> bool:
        # Dans economy.py on passe 'first_work_done' via user_state si besoin,
        # Ici on peut inférer: si last_work devenait non-null à l’instant, gère côté economy (déjà true lors du 1er).
        # Simplifié: si total_earned venait d’augmenter et que quick flag dans user_state:
        if user_state.get("_just_first_work"):
            return self.award(ctx.author.id)
        return False

FIRST_WORK.__class__ = _FirstWork
