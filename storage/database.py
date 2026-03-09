import json
import os
import shutil
import sqlite3
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DATABASE_PATH = Path(os.getenv("SKANAK_DB_PATH", str(DATA_DIR / "skanak.db")))

_LEGACY_STATE_FILES = {
    "economy.lottery": ROOT_DIR / "economy" / "lottery.json",
    "economy.renames": ROOT_DIR / "economy" / "renames.json",
    "counting.state": ROOT_DIR / "counting" / "count.json",
    "meme.index": ROOT_DIR / "meme_sender" / "meme_index.json",
    "fun.cheese_leaderboard": ROOT_DIR / "fun_commands" / "cheese_leaderboard.json",
    "economy.cheese_leaderboard": ROOT_DIR / "economy" / "cheese_leaderboard.json",
}

_LEGACY_USER_STATS_FILE = ROOT_DIR / "economy" / "user_stats.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _connect() -> sqlite3.Connection:
    _ensure_parent_dir(DATABASE_PATH)
    conn = sqlite3.connect(DATABASE_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def initialize_database() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS economy_user_stats (
                user_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_state (
                state_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_meta (
                meta_key TEXT PRIMARY KEY,
                meta_value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def load_all_user_stats() -> Dict[str, Dict[str, Any]]:
    initialize_database()
    stats: Dict[str, Dict[str, Any]] = {}
    with _connect() as conn:
        rows = conn.execute("SELECT user_id, payload FROM economy_user_stats").fetchall()
    for row in rows:
        uid = str(row["user_id"])
        try:
            data = json.loads(row["payload"])
            if isinstance(data, dict):
                stats[uid] = data
        except json.JSONDecodeError:
            continue
    return stats


def save_user_stats(stats: Dict[str, Dict[str, Any]]) -> None:
    initialize_database()
    now = _now_iso()
    with _connect() as conn:
        with conn:
            for uid, payload in stats.items():
                conn.execute(
                    """
                    INSERT INTO economy_user_stats (user_id, payload, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE
                    SET payload=excluded.payload, updated_at=excluded.updated_at
                    """,
                    (str(uid), json.dumps(payload, ensure_ascii=False), now),
                )


def load_app_state(state_key: str, default: Any = None) -> Any:
    initialize_database()
    with _connect() as conn:
        row = conn.execute(
            "SELECT payload FROM app_state WHERE state_key = ?",
            (state_key,),
        ).fetchone()
    if not row:
        return deepcopy(default)
    try:
        return json.loads(row["payload"])
    except json.JSONDecodeError:
        return deepcopy(default)


def save_app_state(state_key: str, value: Any) -> None:
    initialize_database()
    with _connect() as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO app_state (state_key, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(state_key) DO UPDATE
                SET payload=excluded.payload, updated_at=excluded.updated_at
                """,
                (state_key, json.dumps(value, ensure_ascii=False), _now_iso()),
            )


def _state_exists(state_key: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM app_state WHERE state_key = ? LIMIT 1",
            (state_key,),
        ).fetchone()
    return row is not None


def _user_stats_table_empty() -> bool:
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM economy_user_stats").fetchone()
    return not row or int(row["c"]) == 0


def _meta_set(meta_key: str, meta_value: str) -> None:
    with _connect() as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO app_meta (meta_key, meta_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(meta_key) DO UPDATE
                SET meta_value=excluded.meta_value, updated_at=excluded.updated_at
                """,
                (meta_key, meta_value, _now_iso()),
            )


def _backup_legacy_file(path: Path) -> None:
    if not path.exists():
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_dir = DATA_DIR / "legacy_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    dest = backup_dir / f"{path.name}.{stamp}.bak"
    if not dest.exists():
        shutil.copy2(path, dest)


def _load_legacy_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return deepcopy(default)
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return deepcopy(default)


def migrate_legacy_runtime_data() -> None:
    """
    Import legacy JSON runtime files into SQLite once, without deleting originals.
    Safe to call on every startup.
    """
    initialize_database()
    migrated_any = False

    if _user_stats_table_empty() and _LEGACY_USER_STATS_FILE.exists():
        legacy_stats = _load_legacy_json(_LEGACY_USER_STATS_FILE, {})
        if isinstance(legacy_stats, dict) and legacy_stats:
            save_user_stats(legacy_stats)
            _backup_legacy_file(_LEGACY_USER_STATS_FILE)
            migrated_any = True

    for state_key, path in _LEGACY_STATE_FILES.items():
        if _state_exists(state_key):
            continue
        legacy_value = _load_legacy_json(path, None)
        if legacy_value is None:
            continue
        save_app_state(state_key, legacy_value)
        if path.exists():
            _backup_legacy_file(path)
        migrated_any = True

    # Keep metadata for observability; migration remains idempotent and safe to rerun.
    _meta_set("legacy_json_migration_v1_done", "1")
    if migrated_any:
        _meta_set("legacy_json_migration_v1_last_at", _now_iso())
