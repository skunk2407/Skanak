import os, json
from typing import Dict

USER_STATS = os.path.join(os.path.dirname(__file__), 'user_stats.json')

# 💾 Schéma par défaut d'un joueur
DEFAULT_USER: Dict = {
    'cheese': 0,
    'last_work': None,
    'last_daily': None,
    'daily_streak': 0,
    'safe_mode_expiry': 0,
    'safe_mode_permanent': False,
    'next_work_multiplier': 1.0,
    'next_daily_multiplier': 1.0,
    'steal_boost': 0.0,
    'roles': [],
    'badges': [],
    'shop_purchases': 0,
    'spent_in_shop': False,
    'total_shared': 0,
    'total_earned': 0,
    'total_stolen': 0,
    'theft_victims': [],
    'quick_combo': 0,
    'last_action': None,
    'consecutive_stolen_count': 0,
    'last_stolen_time': 0.0,
    'rename_tokens': 0,

    # 🆕 Stat pour ton idée : record de gain en un seul !work
    'max_work_gain': 0,
}

def load_stats() -> Dict:
    if not os.path.exists(USER_STATS):
        return {}
    with open(USER_STATS, 'r') as f:
        return json.load(f)

def save_stats(stats: Dict) -> None:
    with open(USER_STATS, 'w') as f:
        json.dump(stats, f, indent=4)

def get_user_stats(stats: Dict, user_id: int) -> Dict:
    """Retourne la fiche joueur en garantissant toutes les clés du schéma."""
    uid = str(user_id)
    if uid not in stats:
        # copie superficielle OK, les valeurs mutables sont réécrites par setdefault ensuite
        stats[uid] = DEFAULT_USER.copy()
        # listes devront être des copies distinctes
        stats[uid]['roles'] = []
        stats[uid]['badges'] = []
        stats[uid]['theft_victims'] = []
    else:
        user = stats[uid]
        for key, default in DEFAULT_USER.items():
            # pour les listes, on évite de partager des références
            if key not in user:
                user[key] = default if not isinstance(default, list) else list(default)
    return stats[uid]
