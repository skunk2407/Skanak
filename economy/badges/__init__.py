from .base import Badge, grant_badge
from .catalog import BADGES as CATALOG

# === Imports des badges avec logique dédiée ===
from .first_work import FIRST_WORK
from .hoarder import HOARDER
from .streak_7 import STREAK_7
from .streak_30 import STREAK_30
from .wealth_1m import WEALTH_1M
from .speed_runner import SPEED_RUNNER
from .raid_boss import RAID_BOSS
from .master_thief import MASTER_THIEF
from .underdog import UNDERDOG


# --- Hydratation des infos (nom, desc, url) depuis le catalogue ---
def _hydrate_from_catalog(b: Badge):
    meta = CATALOG.get(b.key, {})
    if meta:
        b.name = meta.get("name", b.name)
        b.description = meta.get("description", b.description)
        b.url = meta.get("url", b.url)
    return b


# Registre des badges avec logique Python
_REG = [
    _hydrate_from_catalog(FIRST_WORK),
    _hydrate_from_catalog(HOARDER),
    _hydrate_from_catalog(STREAK_7),
    _hydrate_from_catalog(STREAK_30),
    _hydrate_from_catalog(WEALTH_1M),
    _hydrate_from_catalog(SPEED_RUNNER),
    _hydrate_from_catalog(RAID_BOSS),
    _hydrate_from_catalog(MASTER_THIEF),
    _hydrate_from_catalog(UNDERDOG),
]

REGISTRY = {b.key: b for b in _REG}

# 👉 BADGES = tout le catalogue (pour affichage dans !profile et !badges)
BADGES = CATALOG


# --- API publique ---
def award_badge(user_id: int, key: str) -> bool:
    """
    Attribue un badge :
      - Si badge avec logique (dans REGISTRY), utilise sa méthode .award
      - Sinon, fallback sur grant_badge (ajout direct dans user_stats.json)
    """
    b = REGISTRY.get(key)
    return b.award(user_id) if b else grant_badge(user_id, key)


async def dispatch_badge_event(event: str, ctx, **kwargs):
    """
    Notifie tous les badges de l'événement donné.
    Ex: event="work", "daily", "share", "steal"...
    """
    triggered = []
    for b in REGISTRY.values():
        try:
            if b.on_event(event, ctx, **kwargs):
                triggered.append(b)
        except Exception as e:
            print(f"[Badge {b.key}] Error in on_event: {e}")

    # Feedback visuel pour chaque badge gagné
    for b in triggered:
        embed = b.build_embed(ctx.author)
        if embed:
            await ctx.send(embed=embed)
