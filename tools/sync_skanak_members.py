"""Refresh the public Discord member metadata used by the Cheese leaderboard."""

import json
import os
import urllib.request
from pathlib import Path

BOT_ENV = Path(os.getenv("SKANAK_BOT_ENV", "/opt/SkanakBot/Skanak/.env"))
OUTPUT = Path(os.getenv("SKANAK_MEMBERS_CACHE", "/opt/SkanakBot/Skanak/data/member_cache.json"))


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def avatar_url(user: dict, member: dict, guild_id: str) -> str | None:
    if member.get("avatar"):
        return f"https://cdn.discordapp.com/guilds/{guild_id}/users/{user['id']}/avatars/{member['avatar']}.webp?size=96"
    if user.get("avatar"):
        return f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.webp?size=96"
    return None


def main() -> None:
    env = read_env(BOT_ENV)
    token = env["DISCORD_TOKEN"]
    guild_id = env["DISCORD_GUILD_ID"]
    request = urllib.request.Request(
        f"https://discord.com/api/v10/guilds/{guild_id}/members?limit=1000",
        headers={"Authorization": f"Bot {token}", "User-Agent": "SkanakMemberSync/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        members = json.load(response)

    cache = {}
    for member in members:
        user = member.get("user", {})
        user_id = str(user.get("id", ""))
        if not user_id or user.get("bot"):
            continue
        cache[user_id] = {
            "display_name": member.get("nick") or user.get("global_name") or user.get("username") or "Unknown member",
            "avatar_url": avatar_url(user, member, guild_id),
        }

    temporary = OUTPUT.with_suffix(".tmp")
    temporary.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temporary.chmod(0o644)
    temporary.replace(OUTPUT)
    print(f"members_cached={len(cache)}")


if __name__ == "__main__":
    main()
