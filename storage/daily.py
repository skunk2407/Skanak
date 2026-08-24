"""Atomic daily reward shared by Discord and the Toxic Flaggers website."""

import json
import sqlite3
from datetime import datetime

from storage.database import DATABASE_PATH, initialize_database


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA foreign_keys=ON;")
    return connection


def _ensure_transactions(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS economy_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            balance_after INTEGER NOT NULL,
            action TEXT NOT NULL,
            source TEXT NOT NULL,
            metadata TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS economy_transactions_user_created "
        "ON economy_transactions(user_id, created_at DESC)"
    )


def claim_daily(user_id: int | str, source: str = "discord", now: datetime | None = None) -> dict:
    initialize_database()
    uid = str(user_id)
    claimed_at = now or datetime.utcnow()
    connection = _connect()

    try:
        connection.execute("BEGIN IMMEDIATE")
        _ensure_transactions(connection)
        row = connection.execute(
            "SELECT payload FROM economy_user_stats WHERE user_id = ? LIMIT 1",
            (uid,),
        ).fetchone()
        user = json.loads(row["payload"]) if row else {}

        last_daily = user.get("last_daily")
        if last_daily:
            last = datetime.fromisoformat(last_daily)
            elapsed = int((claimed_at - last).total_seconds())
            if elapsed < 86400:
                connection.rollback()
                return {
                    "claimed": False,
                    "remaining_seconds": max(1, 86400 - elapsed),
                    "streak": int(user.get("daily_streak", 0)),
                    "balance": int(user.get("cheese", 0)),
                }
            if elapsed // 86400 > 1:
                user["daily_streak"] = 0

        streak = int(user.get("daily_streak", 0))
        if streak < 30:
            reward = 100 + streak * 25
            streak += 1
        else:
            reward = 100
            streak = 1

        reward = int(reward * float(user.get("next_daily_multiplier", 1.0)))
        user["next_daily_multiplier"] = 1.0
        user["cheese"] = int(user.get("cheese", 0)) + reward
        user["total_earned"] = int(user.get("total_earned", 0)) + reward
        user["last_daily"] = claimed_at.isoformat()
        user["daily_count"] = int(user.get("daily_count", 0)) + 1
        user["daily_streak"] = streak
        user["last_action"] = "daily"
        user["cheese_since_last_spend"] = int(user.get("cheese_since_last_spend", 0)) + reward
        user["max_cheese"] = max(int(user.get("max_cheese", 0)), user["cheese"])
        updated_at = claimed_at.isoformat()

        connection.execute(
            """
            INSERT INTO economy_user_stats (user_id, payload, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE
            SET payload=excluded.payload, updated_at=excluded.updated_at
            """,
            (uid, json.dumps(user, ensure_ascii=False), updated_at),
        )
        connection.execute(
            """
            INSERT INTO economy_transactions
                (user_id, amount, balance_after, action, source, metadata, created_at)
            VALUES (?, ?, ?, 'daily', ?, ?, ?)
            """,
            (uid, reward, user["cheese"], source, json.dumps({"streak": streak}), updated_at),
        )
        connection.commit()

        return {"claimed": True, "reward": reward, "streak": streak, "balance": user["cheese"]}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
