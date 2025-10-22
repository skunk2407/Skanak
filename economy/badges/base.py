# base.py
import os, json, time
from dataclasses import dataclass

# Chemin vers le JSON partagé par l'économie
ECONOMY_DIR = os.path.dirname(os.path.dirname(__file__))
STATS_PATH  = os.path.join(ECONOMY_DIR, "user_stats.json")

def _load_stats():
    if not os.path.exists(STATS_PATH):
        with open(STATS_PATH, "w") as f: json.dump({}, f)
    with open(STATS_PATH, "r") as f:
        return json.load(f)

def _save_stats(stats: dict):
    with open(STATS_PATH, "w") as f:
        json.dump(stats, f, indent=4)

def _ensure_user(stats: dict, uid: int):
    suid = str(uid)
    if suid not in stats: stats[suid] = {"badges": []}
    stats[suid].setdefault("badges", [])
    return stats[suid]

def grant_badge(user_id: int, key: str) -> bool:
    """Ajoute le badge au JSON si non possédé. Retourne True si nouveau."""
    stats = _load_stats()
    user  = _ensure_user(stats, user_id)
    if key not in user["badges"]:
        user["badges"].append(key)
        _save_stats(stats)
        return True
    return False

@dataclass
class Badge:
    key: str
    name: str
    url: str
    description: str = ""

    # Hooks d’événements (retourne True si le badge vient d’être gagné)
    def on_work(self, ctx, user_state: dict, stats: dict) -> bool: return False
    def on_daily(self, ctx, user_state: dict, stats: dict) -> bool: return False
    def on_share(self, ctx, sender_state: dict, receiver_state: dict, amount: int, stats: dict) -> bool: return False
    def on_steal(self, ctx, thief_state: dict, victim_state: dict, stolen: int, stats: dict) -> bool: return False

    def award(self, user_id: int) -> bool:
        return grant_badge(user_id, self.key)
