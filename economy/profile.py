import os
from io import BytesIO
from typing import List, Optional, Tuple

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageOps

from economy.badges import BADGES
from economy.stats import get_user_stats, load_stats

BASE_DIR = os.path.dirname(__file__)
BADGES_DIR = os.path.join(BASE_DIR, "badges", "images", "resized")
SPRITE_DIR = os.path.join(BASE_DIR, "badges", "images", "sprite")
PROFILE_CARD_DIR = os.path.join(SPRITE_DIR, "profile_cards")
BADGES_PER_PAGE = 6


class BadgePaginationView(discord.ui.View):
    def __init__(self, author_id: int, badge_items: List[Tuple[str, dict]], page_size: int = BADGES_PER_PAGE):
        super().__init__(timeout=180)
        self.author_id = author_id
        self.badge_items = badge_items
        self.page_size = page_size
        self.current_page = 0
        self.total_pages = max(1, (len(badge_items) + page_size - 1) // page_size)
        self.message: Optional[discord.Message] = None
        self._refresh_buttons()

    def _refresh_buttons(self):
        self.previous_btn.disabled = self.current_page <= 0
        self.next_btn.disabled = self.current_page >= self.total_pages - 1

    def _current_slice(self) -> List[Tuple[str, dict]]:
        start = self.current_page * self.page_size
        end = start + self.page_size
        return self.badge_items[start:end]

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Badge Guide",
            description="Here is how to unlock each badge:",
            color=discord.Color.blue(),
        )
        for _, info in self._current_slice():
            embed.add_field(
                name=info.get("name", "Unknown badge"),
                value=info.get("description", "-"),
                inline=False,
            )
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages}")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the command author can use these buttons.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _existing_badge_images(self, badge_keys: List[str]) -> List[str]:
        paths = []
        for key in badge_keys:
            path = os.path.join(BADGES_DIR, f"{key}.png")
            if os.path.isfile(path):
                paths.append(path)
        return paths

    def _load_font(self, size: int, bold: bool = False):
        candidates = []
        if os.name == "nt":
            if bold:
                candidates.append("C:/Windows/Fonts/arialbd.ttf")
            candidates.append("C:/Windows/Fonts/arial.ttf")
        else:
            if bold:
                candidates.append("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
            candidates.append("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

        for path in candidates:
            if os.path.isfile(path):
                try:
                    return ImageFont.truetype(path, size=size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def _paste_circular_avatar(self, card: Image.Image, avatar: Image.Image, x: int, y: int, size: int):
        avatar = avatar.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        card.paste(avatar, (x, y), mask)

    async def build_profile_card(
        self,
        member: discord.Member,
        entry: dict,
        badge_keys: List[str],
    ) -> Optional[str]:
        width, height = 1000, 540
        card = Image.new("RGBA", (width, height), (18, 24, 33, 255))
        draw = ImageDraw.Draw(card)

        # Background layers
        draw.rounded_rectangle((20, 20, width - 20, height - 20), radius=26, fill=(29, 38, 51, 255))
        draw.rounded_rectangle((36, 36, width - 36, height - 36), radius=22, fill=(35, 47, 63, 255))
        draw.rectangle((36, 36, 48, height - 36), fill=(72, 187, 120, 255))

        title_font = self._load_font(46, bold=True)
        big_font = self._load_font(32, bold=True)
        label_font = self._load_font(24, bold=False)
        value_font = self._load_font(27, bold=True)
        badge_title_font = self._load_font(22, bold=True)

        # Avatar
        avatar_img = None
        try:
            avatar_bytes = await member.display_avatar.with_size(256).read()
            avatar_img = Image.open(BytesIO(avatar_bytes))
        except Exception:
            avatar_img = None

        if avatar_img is not None:
            self._paste_circular_avatar(card, avatar_img, x=70, y=72, size=150)
            draw.ellipse((70, 72, 220, 222), outline=(94, 234, 140, 255), width=4)

        # Title block
        draw.text((250, 78), f"{member.display_name}", font=title_font, fill=(245, 247, 250, 255))
        draw.text((250, 132), "PLAYER PROFILE", font=label_font, fill=(163, 179, 200, 255))

        cheese = int(entry.get("cheese", 0))
        max_cheese = int(entry.get("max_cheese", cheese))
        purchases = int(entry.get("shop_purchases", 0))
        max_gain = int(entry.get("max_work_gain", 0))

        stats_left = 70
        stats_top = 258
        line_gap = 52
        stat_rows = [
            ("Cheese Balance", f"{cheese:,}"),
            ("All-time Max Cheese", f"{max_cheese:,}"),
            ("Total Items Bought", f"{purchases:,}"),
            ("Best !work Gain", f"{max_gain:,}"),
        ]

        for idx, (label, value) in enumerate(stat_rows):
            y = stats_top + idx * line_gap
            draw.text((stats_left, y), label, font=label_font, fill=(186, 199, 216, 255))
            draw.text((430, y), value, font=value_font, fill=(255, 223, 133, 255))

        # Badges
        draw.text((70, 470), "Unlocked Badges", font=badge_title_font, fill=(224, 233, 244, 255))
        badge_paths = self._existing_badge_images(badge_keys)[:8]
        badge_x = 330
        badge_y = 445
        badge_size = 64
        badge_gap = 14

        if badge_paths:
            for i, path in enumerate(badge_paths):
                try:
                    badge = Image.open(path).convert("RGBA")
                    badge = ImageOps.contain(badge, (badge_size, badge_size), Image.Resampling.LANCZOS)
                    x = badge_x + i * (badge_size + badge_gap)
                    card.paste(badge, (x, badge_y), badge)
                except Exception:
                    continue
        else:
            draw.text((330, 470), "No badges yet", font=label_font, fill=(150, 160, 174, 255))

        os.makedirs(PROFILE_CARD_DIR, exist_ok=True)
        out = os.path.join(PROFILE_CARD_DIR, f"{member.id}_profile.png")
        card.save(out, optimize=True)
        return out

    @commands.command(name="profile")
    async def profile(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author

        stats = load_stats()
        entry = get_user_stats(stats, member.id)
        badges = entry.get("badges", [])
        known_badges = [b for b in badges if b in BADGES]

        card_path = await self.build_profile_card(member, entry, known_badges)
        if card_path and os.path.isfile(card_path):
            file = discord.File(card_path, filename="profile_card.png")
            embed = discord.Embed(color=discord.Color.green())
            embed.set_image(url="attachment://profile_card.png")
            await ctx.send(embed=embed, file=file)
            return

        # Fallback (if image generation fails)
        purchases = int(entry.get("shop_purchases", 0))
        max_gain = int(entry.get("max_work_gain", 0))
        max_cheese = int(entry.get("max_cheese", entry.get("cheese", 0)))
        embed = discord.Embed(
            title=f"{member.display_name}'s Profile",
            color=discord.Color.green(),
            description=(
                f"Cheese Balance: **{entry.get('cheese', 0):,}**\n"
                f"All-time Max Cheese: **{max_cheese:,}**\n"
                f"Total Items Bought: **{purchases}**\n"
                f"Best !work gain: **{max_gain:,}**"
            ),
        )
        await ctx.send(embed=embed)

    @commands.command(name="badges")
    async def badges(self, ctx):
        badge_items = list(BADGES.items())
        if not badge_items:
            return await ctx.send("No badges configured.")

        view = BadgePaginationView(ctx.author.id, badge_items)
        message = await ctx.send(embed=view.build_embed(), view=view)
        view.message = message


async def setup(bot):
    await bot.add_cog(ProfileCog(bot))

