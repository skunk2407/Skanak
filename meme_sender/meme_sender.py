import discord
from discord.ext import commands, tasks
import os, json, random, asyncio, time
from datetime import datetime, timedelta, timezone

INDEX_PATH = os.path.join(os.path.dirname(__file__), "meme_index.json")
USED_COOLDOWN_DAYS = 30      # ne pas re-poster un meme utilisé < 30 jours
MIN_AGE_DAYS = 90            # ne poster que des memes âgés de > 90 jours
BATCH_SIZE = 400             # messages parcourus par vague d'indexation
BATCH_SLEEP = 30             # pause entre vagues (sec) pour éviter ratelimit
EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov")

def now_utc_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()

def load_index():
    if not os.path.exists(INDEX_PATH):
        return {"items": {}, "last_cursor_id": None}
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_index(idx):
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=2)

class MemeSender(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.index = load_index()
        self._indexing = False
        self.send_meme.start()
        self.backfill_index.start()

    # ========== INDEXATION PROGRESSIVE ==========
    @tasks.loop(minutes=5, reconnect=True)
    async def backfill_index(self):
        """Par petites vagues, on complète l'index pour remonter très loin dans l'historique sans se faire rate-limit."""
        channel_id = int(os.getenv("MEME_CHANNEL_ID", "0"))
        channel = self.bot.get_channel(channel_id)
        if channel is None or self._indexing:
            return

        self._indexing = True
        try:
            before = None
            # on reprend au dernier curseur si on l'a
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

                # met à jour le curseur au fur et à mesure
                self.index["last_cursor_id"] = str(msg.id)

            if collected:
                save_index(self.index)
                print(f"[meme-index] +{collected} items (total {len(self.index['items'])})")
            # petite pause entre vagues
            await asyncio.sleep(BATCH_SLEEP)
        except Exception as e:
            print(f"[meme-index][err] {e}")
        finally:
            self._indexing = False

    @backfill_index.before_loop
    async def before_backfill(self):
        await self.bot.wait_until_ready()

    # ========== ENVOI PÉRIODIQUE ==========
    @tasks.loop(hours=3, reconnect=True)
    async def send_meme(self):
        print("[meme] loop tick")
        try:
            channel_id = int(os.getenv("MEME_CHANNEL_ID", "0"))
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                print(f"[meme] channel {channel_id} not found")
                return

            # Limite d’upload du serveur
            max_size = getattr(channel.guild, "filesize_limit", 8_000_000)

            # Filtre: assez ancien + pas utilisé récemment + pas blacklist + taille OK
            now = datetime.now(tz=timezone.utc)
            min_age_dt = now - timedelta(days=MIN_AGE_DAYS)
            cooldown_dt = now - timedelta(days=USED_COOLDOWN_DAYS)

            candidates = []
            for key, it in self.index["items"].items():
                if it["blacklisted"]:
                    continue
                try:
                    created = datetime.fromisoformat(it["created_at"])
                except Exception:
                    continue
                if created > min_age_dt:
                    continue
                if it["size"] is not None and it["size"] > max_size:
                    continue
                last_used = datetime.fromisoformat(it["last_used_at"]) if it["last_used_at"] else None
                if last_used and last_used > cooldown_dt:
                    continue
                candidates.append((key, it))

            if not candidates:
                print("[meme] aucun candidat (index encore court ?)")
                return

            key, it = random.choice(candidates)
            temp_dir = os.path.join(os.path.dirname(__file__), "temp")
            os.makedirs(temp_dir, exist_ok=True)
            file_path = os.path.join(temp_dir, it["filename"])

            # On retélécharge depuis l’attachment d’origine (plus fiable que l’URL si signée)
            try:
                msg = await channel.fetch_message(it["message_id"])
                att = next((a for a in msg.attachments if a.id == it["attachment_id"]), None)
                if att is None:
                    raise RuntimeError("attachment plus présent")
                await att.save(file_path)
                await channel.send(file=discord.File(file_path))
                it["last_used_at"] = now_utc_iso()
                it["uses"] = int(it.get("uses", 0)) + 1
                save_index(self.index)
                print(f"[meme] posté: {it['filename']} (uses={it['uses']})")
            except discord.HTTPException as e:
                print(f"[meme][HTTP] {e}")
                # Erreurs d’upload → si taille/permission : blacklist pour éviter de re-essayer en boucle
                if "Request entity too large" in str(e):
                    it["blacklisted"] = True
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
