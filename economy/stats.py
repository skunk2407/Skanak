from typing import Dict

from storage.database import load_all_user_stats, save_user_stats

# Default schema for an economy user profile
DEFAULT_USER: Dict = {
    "cheese": 0,
    "last_work": None,
    "last_daily": None,
    "daily_count": 0,
    "daily_streak": 0,
    "safe_mode_expiry": 0,
    "safe_mode_permanent": False,
    "next_work_multiplier": 1.0,
    "next_daily_multiplier": 1.0,
    "steal_boost": 0.0,
    "roles": [],
    "badges": [],
    "shop_purchases": 0,
    "spent_in_shop": False,
    "total_shared": 0,
    "share_count": 0,
    "steal_count": 0,
    "total_earned": 0,
    "total_stolen": 0,
    "theft_victims": [],
    "quick_combo": 0,
    "last_action": None,
    "consecutive_stolen_count": 0,
    "last_stolen_time": 0.0,
    "rename_tokens": 0,
    "max_work_gain": 0,
    "work_count": 0,
    # New stat: highest all-time cheese balance reached by the user
    "max_cheese": 0,
}


def load_stats() -> Dict:
    return load_all_user_stats()


def save_stats(stats: Dict) -> None:
    # Keep a persistent peak balance.
    for user in stats.values():
        if not isinstance(user, dict):
            continue
        current_cheese = int(user.get("cheese", 0) or 0)
        current_peak = int(user.get("max_cheese", 0) or 0)
        user["max_cheese"] = max(current_peak, current_cheese)
    save_user_stats(stats)


def get_user_stats(stats: Dict, user_id: int) -> Dict:
    """Return one user profile while enforcing full schema defaults."""
    uid = str(user_id)
    if uid not in stats:
        stats[uid] = DEFAULT_USER.copy()
        stats[uid]["roles"] = []
        stats[uid]["badges"] = []
        stats[uid]["theft_victims"] = []
    else:
        user = stats[uid]
        for key, default in DEFAULT_USER.items():
            if key not in user:
                user[key] = default if not isinstance(default, list) else list(default)
        user["max_cheese"] = max(int(user.get("max_cheese", 0) or 0), int(user.get("cheese", 0) or 0))
        # Keep total_earned consistent for older profiles that predate this stat.
        user["total_earned"] = max(
            int(user.get("total_earned", 0) or 0),
            int(user.get("max_cheese", 0) or 0),
            int(user.get("cheese", 0) or 0),
        )
    return stats[uid]
