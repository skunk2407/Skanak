import asyncio
import os
import random
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands, tasks

from storage.database import load_app_state, save_app_state

MEME_INDEX_STATE_KEY = "meme.index"
USED_COOLDOWN_DAYS = 30
MIN_AGE_DAYS = 90
BATCH_SIZE = 400
BATCH_SLEEP = 30
EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov")


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() not in {"0", "false", "no", "off"}


def now_utc_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def load_index():
    idx = load_app_state(MEME_INDEX_STATE_KEY, default={"items": {}, "last_cursor_id": None})
    if not isinstance(idx, dict):
        return {"items": {}, "last_cursor_id": None}
    idx.setdefault("items", {})
    idx.setdefault("last_cursor_id", None)
    return idx


def save_index(idx):
    save_app_state(MEME_INDEX_STATE_KEY, idx)


class MemeSender(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.index = load_index()
        self._indexing = False

        self.auto_meme_enabled = _env_flag("SKANAK_AUTO_MEME_ENABLED", default=True)
        self.meme_backfill_enabled = _env_flag(
            "SKANAK_MEME_BACKFILL_ENABLED",
            default=self.auto_meme_enabled,
        )

        if self.auto_meme_enabled:
            self.send_meme.start()
        else:
            print("[meme] auto meme posting disabled by SKANAK_AUTO_MEME_ENABLED")

        if self.meme_backfill_enabled:
            self.backfill_index.start()
        else:
            print("[meme-index] backfill disabled by SKANAK_MEME_BACKFILL_ENABLED")

    def cog_unload(self):
        if self.send_meme.is_running():
            self.send_meme.cancel()
        if self.backfill_index.is_running():
            self.backfill_index.cancel()

    @tasks.loop(minutes=5, reconnect=True)
    async def backfill_index(self):
        channel_id = int(os.getenv("MEME_CHANNEL_ID", "0"))
        channel = self.bot.get_channel(channel_id)
        if channel is None or self._indexing:
            return

        self._indexing = True
        try:
            before = None
            cursor = self.index.get("last_cursor_id")
            if cursor:
                try:
                    before = await channel.fetch_message(int(cursor))
                except Exception:
                    before = None

            collected = 0
            async for msg in channel.history(limit=BATCH_SIZE, before=before, oldest_first=False):
                for att in msg.attachments:
                    name = (att.filename or "").lower()
                    if not name.endswith(EXTS):
                        continue
                    key = f"{msg.id}:{att.id}"
                    if key in self.index["items"]:
                        continue
                    self.index["items"][key] = {
                        "message_id": msg.id,
                        "attachment_id": att.id,
                        "channel_id": channel.id,
                        "filename": att.filename,
                        "size": att.size,
                        "url": att.url,
                        "created_at": msg.created_at.replace(tzinfo=timezone.utc).isoformat(),
                        "last_used_at": None,
                        "uses": 0,
                        "blacklisted": False,
                    }
                    collected += 1

                self.index["last_cursor_id"] = str(msg.id)

            if collected:
                save_index(self.index)
                print(f"[meme-index] +{collected} items (total {len(self.index['items'])})")
            await asyncio.sleep(BATCH_SLEEP)
        except Exception as e:
            print(f"[meme-index][err] {e}")
        finally:
            self._indexing = False

    @backfill_index.before_loop
    async def before_backfill(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=3, reconnect=True)
    async def send_meme(self):
        print("[meme] loop tick")
        try:
            channel_id = int(os.getenv("MEME_CHANNEL_ID", "0"))
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                print(f"[meme] channel {channel_id} not found")
                return

            max_size = getattr(channel.guild, "filesize_limit", 8_000_000)
            now = datetime.now(tz=timezone.utc)
            min_age_dt = now - timedelta(days=MIN_AGE_DAYS)
            cooldown_dt = now - timedelta(days=USED_COOLDOWN_DAYS)

            candidates = []
            for key, item in self.index["items"].items():
                if item["blacklisted"]:
                    continue
                try:
                    created = datetime.fromisoformat(item["created_at"])
                except Exception:
                    continue
                if created > min_age_dt:
                    continue
                if item["size"] is not None and item["size"] > max_size:
                    continue
                last_used = datetime.fromisoformat(item["last_used_at"]) if item["last_used_at"] else None
                if last_used and last_used > cooldown_dt:
                    continue
                candidates.append((key, item))

            if not candidates:
                print("[meme] no candidate found")
                return

            key, item = random.choice(candidates)
            temp_dir = os.path.join(os.path.dirname(__file__), "temp")
            os.makedirs(temp_dir, exist_ok=True)
            file_path = os.path.join(temp_dir, item["filename"])

            try:
                msg = await channel.fetch_message(item["message_id"])
                att = next((a for a in msg.attachments if a.id == item["attachment_id"]), None)
                if att is None:
                    raise RuntimeError("attachment not available")
                await att.save(file_path)
                await channel.send(file=discord.File(file_path))
                item["last_used_at"] = now_utc_iso()
                item["uses"] = int(item.get("uses", 0)) + 1
                save_index(self.index)
                print(f"[meme] posted: {item['filename']} (uses={item['uses']})")
            except discord.HTTPException as e:
                print(f"[meme][HTTP] {e}")
                if "Request entity too large" in str(e):
                    item["blacklisted"] = True
                    save_index(self.index)
            except Exception as e:
                print(f"[meme][err] {e}")
            finally:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass
        except Exception as e:
            print(f"[meme][fatal] {e}")

    @send_meme.before_loop
    async def before_send(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(MemeSender(bot))

