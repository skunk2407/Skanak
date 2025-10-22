import os
import discord
from discord.ext import commands
from PIL import Image
from typing import Optional, List

from economy.stats import load_stats, get_user_stats
from economy.badges import BADGES

BASE_DIR = os.path.dirname(__file__)
BADGES_DIR = os.path.join(BASE_DIR, "badges", "images", "resized")
SPRITE_DIR = os.path.join(BASE_DIR, "badges", "images", "sprite")

class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _existing_badge_images(self, badge_keys: List[str]) -> List[str]:
        """Retourne la liste des chemins .png existants correspondant aux clés."""
        paths = []
        for key in badge_keys:
            p = os.path.join(BADGES_DIR, f"{key}.png")
            if os.path.isfile(p):
                paths.append(p)
        return paths

    def build_badges_sprite(self, badge_keys: List[str], user_id: str) -> Optional[str]:
        """
        Construit un sprite horizontal des badges du user.
        Retourne le chemin du fichier généré ou None si rien à afficher.
        """
        paths = self._existing_badge_images(badge_keys)
        if not paths:
            return None

        images = [Image.open(p).convert("RGBA") for p in paths]
        total_w = sum(img.width for img in images)
        max_h = max(img.height for img in images)
        sprite = Image.new("RGBA", (total_w, max_h), (0, 0, 0, 0))

        x = 0
        for img in images:
            sprite.paste(img, (x, 0), img)
            x += img.width

        os.makedirs(SPRITE_DIR, exist_ok=True)
        out = os.path.join(SPRITE_DIR, f"{user_id}_badges.png")
        # Écrase silencieusement l’ancien sprite
        try:
            sprite.save(out, optimize=True)
        finally:
            for img in images:
                img.close()
        return out

    @commands.command(name="profile")
    async def profile(self, ctx, member: discord.Member = None):
        """
        Affiche le profil d'un membre (ou de soi) :
        - Solde cheese
        - Record max gain !work
        - Badges (sprite)
        - Total d'achats
        """
        if member is None:
            member = ctx.author

        stats = load_stats()
        entry = get_user_stats(stats, member.id)
        badges = entry.get("badges", [])
        purchases = entry.get("shop_purchases", 0)
        max_gain = entry.get("max_work_gain", 0)   # 🆕 record !work

        embed = discord.Embed(
            title=f"{member.display_name}'s Profile",
            color=discord.Color.green(),
        )
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)

        embed.description = (
            f"🧀 Cheese Balance: **{entry.get('cheese', 0):,}**\n"
            f"🛍️ Total Items Bought: **{purchases}**\n"
            f"🔝 Best !work gain: **{max_gain:,}** 🧀"
        )

        # Section Badges
        if badges:
            known = [b for b in badges if b in BADGES]
            if known:
                embed.add_field(
                    name="🏅 Badges",
                    value="Your unlocked badges below 👇",
                    inline=False,
                )
                sprite_path = self.build_badges_sprite(known, str(member.id))
                if sprite_path:
                    file = discord.File(sprite_path, filename="badges.png")
                    embed.set_image(url="attachment://badges.png")
                    await ctx.send(embed=embed, file=file)
                    return

        # Aucun badge ou aucune image dispo → envoi sans image
        if not badges:
            embed.add_field(name="🏅 Badges", value="None yet!", inline=False)
        else:
            embed.add_field(
                name="🏅 Badges",
                value="(No local images found for your badges)",
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command(name="badges")
    async def badges(self, ctx):
        """Liste tous les badges et leurs conditions."""
        embed = discord.Embed(
            title="🏅 Badge Guide",
            description="Here’s how to unlock each badge:",
            color=discord.Color.blue(),
        )
        for key, info in BADGES.items():
            embed.add_field(
                name=info["name"],
                value=info.get("description", "—"),
                inline=False,
            )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ProfileCog(bot))
