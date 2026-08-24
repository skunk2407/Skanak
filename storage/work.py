"""Atomic work reward shared by Discord and the Toxic Flaggers website."""

import json
import random
import sqlite3
from datetime import datetime

from storage.database import DATABASE_PATH, initialize_database


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA foreign_keys=ON;")
    return connection


def claim_work(user_id: int | str, source: str = "discord", now: datetime | None = None) -> dict:
    initialize_database()
    uid = str(user_id)
    claimed_at = now or datetime.utcnow()
    connection = _connect()

    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT payload FROM economy_user_stats WHERE user_id = ? LIMIT 1", (uid,)).fetchone()
        user = json.loads(row["payload"]) if row else {}

        if user.get("last_work"):
            elapsed = int((claimed_at - datetime.fromisoformat(user["last_work"])).total_seconds())
            if elapsed < 7200:
                connection.rollback()
                return {"claimed": False, "remaining_seconds": max(1, 7200 - elapsed), "balance": int(user.get("cheese", 0))}

        base = random.randint(0, 350)
        reward = int(base * float(user.get("next_work_multiplier", 1.0)))
        user["next_work_multiplier"] = 1.0
        user["cheese"] = int(user.get("cheese", 0)) + reward
        user["total_earned"] = int(user.get("total_earned", 0)) + reward
        user["last_work"] = claimed_at.isoformat()
        user["work_count"] = int(user.get("work_count", 0)) + 1
        user["cheese_since_last_spend"] = int(user.get("cheese_since_last_spend", 0)) + reward
        user["max_work_gain"] = max(int(user.get("max_work_gain", 0)), reward)
        user["max_cheese"] = max(int(user.get("max_cheese", 0)), user["cheese"])

        quick_combo = 1
        if user.get("last_action") == "daily" and user.get("last_daily"):
            quick_combo = int(user.get("quick_combo", 0)) + 1 if (claimed_at - datetime.fromisoformat(user["last_daily"])).total_seconds() <= 60 else 1
        user["quick_combo"] = quick_combo
        user["last_action"] = "work"
        updated_at = claimed_at.isoformat()

        connection.execute(
            """INSERT INTO economy_user_stats (user_id, payload, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at""",
            (uid, json.dumps(user, ensure_ascii=False), updated_at),
        )
        connection.execute(
            """INSERT INTO economy_transactions
            (user_id, amount, balance_after, action, source, metadata, created_at)
            VALUES (?, ?, ?, 'work', ?, ?, ?)""",
            (uid, reward, user["cheese"], source, json.dumps({"base": base, "work_count": user["work_count"]}), updated_at),
        )
        connection.commit()
        return {"claimed": True, "reward": reward, "balance": user["cheese"], "work_count": user["work_count"], "max_work_gain": user["max_work_gain"]}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
