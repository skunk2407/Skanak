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
BADGE_GUIDE_PER_PAGE = 6
UNLOCKED_BADGES_PER_PAGE = 8


class BadgeGuidePaginationView(discord.ui.View):
    def __init__(self, author_id: int, badge_items: List[Tuple[str, dict]], page_size: int = BADGE_GUIDE_PER_PAGE):
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

    def _current_slice(self):
        start = self.current_page * self.page_size
        end = start + self.page_size
        return self.badge_items[start:end]

    def build_embed(self):
        embed = discord.Embed(
            title="Badge Guide",
            description="How to unlock each badge:",
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


class UnlockedBadgesPaginationView(discord.ui.View):
    def __init__(
        self,
        author_id: int,
        target: discord.Member,
        unlocked_badges: List[Tuple[str, dict]],
        page_size: int = UNLOCKED_BADGES_PER_PAGE,
    ):
        super().__init__(timeout=180)
        self.author_id = author_id
        self.target = target
        self.unlocked_badges = unlocked_badges
        self.page_size = page_size
        self.current_page = 0
        self.total_pages = max(1, (len(unlocked_badges) + page_size - 1) // page_size)
        self.message: Optional[discord.Message] = None
        self._refresh_buttons()

    def _refresh_buttons(self):
        self.previous_btn.disabled = self.current_page <= 0
        self.next_btn.disabled = self.current_page >= self.total_pages - 1

    def _current_slice(self):
        start = self.current_page * self.page_size
        end = start + self.page_size
        return self.unlocked_badges[start:end]

    def build_embed(self):
        embed = discord.Embed(
            title=f"{self.target.display_name} - Unlocked Badges",
            color=discord.Color.gold(),
        )
        if self.target.avatar:
            embed.set_thumbnail(url=self.target.avatar.url)

        if not self.unlocked_badges:
            embed.description = "No badges unlocked yet."
        else:
            lines = []
            for _, info in self._current_slice():
                name = info.get("name", "Unknown badge")
                desc = info.get("description", "-")
                lines.append(f"• **{name}** - {desc}")
            embed.description = "\n".join(lines)

        embed.set_footer(
            text=(
                f"Page {self.current_page + 1}/{self.total_pages} | "
                f"Total unlocked: {len(self.unlocked_badges)}"
            )
        )
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
            candidates.extend(
                [
                    "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
                    "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
                ]
            )
        else:
            candidates.extend(
                [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                    if bold
                    else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                ]
            )

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

    def _draw_gradient(self, img: Image.Image):
        draw = ImageDraw.Draw(img)
        w, h = img.size
        for y in range(h):
            t = y / max(1, h - 1)
            r = int(16 + (26 - 16) * t)
            g = int(24 + (38 - 24) * t)
            b = int(36 + (58 - 36) * t)
            draw.line([(0, y), (w, y)], fill=(r, g, b, 255))

    async def build_profile_card(self, member: discord.Member, entry: dict, badge_keys: List[str]) -> Optional[str]:
        width, height = 1100, 640
        card = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        self._draw_gradient(card)
        draw = ImageDraw.Draw(card)

        # Main panel
        draw.rounded_rectangle((28, 24, width - 28, height - 24), radius=24, fill=(20, 31, 46, 245))
        draw.rounded_rectangle((42, 38, width - 42, height - 38), radius=18, outline=(75, 214, 138, 255), width=3)

        title_font = self._load_font(48, bold=True)
        subtitle_font = self._load_font(23, bold=False)
        label_font = self._load_font(28, bold=False)
        value_font = self._load_font(32, bold=True)
        badge_label_font = self._load_font(24, bold=True)
        hint_font = self._load_font(20, bold=False)

        # Avatar
        avatar_img = None
        try:
            avatar_bytes = await member.display_avatar.with_size(256).read()
            avatar_img = Image.open(BytesIO(avatar_bytes))
        except Exception:
            avatar_img = None

        if avatar_img is not None:
            self._paste_circular_avatar(card, avatar_img, x=72, y=72, size=190)
            draw.ellipse((72, 72, 262, 262), outline=(106, 255, 167, 255), width=5)

        # Header text
        draw.text((300, 86), member.display_name, font=title_font, fill=(243, 248, 255, 255))
        draw.text((302, 146), "Community Economy Profile", font=subtitle_font, fill=(153, 176, 204, 255))

        cheese = int(entry.get("cheese", 0))
        max_cheese = int(entry.get("max_cheese", cheese))
        purchases = int(entry.get("shop_purchases", 0))
        max_gain = int(entry.get("max_work_gain", 0))

        # Stats blocks
        stats = [
            ("Cheese Balance", f"{cheese:,}"),
            ("All-time Max Cheese", f"{max_cheese:,}"),
            ("Total Items Bought", f"{purchases:,}"),
            ("Best !work Gain", f"{max_gain:,}"),
        ]

        x_label = 78
        x_value = 500
        y_start = 302
        line_gap = 60
        for idx, (label, value) in enumerate(stats):
            y = y_start + idx * line_gap
            draw.text((x_label, y), label, font=label_font, fill=(183, 202, 226, 255))
            draw.text((x_value, y), value, font=value_font, fill=(255, 221, 130, 255))

        # Badge preview (kept clean on profile card)
        draw.text((78, 548), "Badge Preview", font=badge_label_font, fill=(231, 240, 252, 255))
        badge_paths = self._existing_badge_images(badge_keys)
        preview_count = 5
        shown = badge_paths[:preview_count]
        badge_x = 330
        badge_y = 520
        badge_size = 82
        badge_gap = 16

        if shown:
            for i, path in enumerate(shown):
                try:
                    badge = Image.open(path).convert("RGBA")
                    badge = ImageOps.contain(badge, (badge_size, badge_size), Image.Resampling.LANCZOS)
                    x = badge_x + i * (badge_size + badge_gap)
                    card.paste(badge, (x, badge_y), badge)
                except Exception:
                    continue
        else:
            draw.text((330, 548), "No badges unlocked yet.", font=hint_font, fill=(145, 165, 188, 255))

        remaining = max(0, len(badge_paths) - preview_count)
        if remaining > 0:
            draw.text(
                (850, 550),
                f"+{remaining} more",
                font=hint_font,
                fill=(145, 207, 255, 255),
            )
        draw.text(
            (850, 576),
            "Use !mybadges",
            font=hint_font,
            fill=(145, 207, 255, 255),
        )

        os.makedirs(PROFILE_CARD_DIR, exist_ok=True)
        output_path = os.path.join(PROFILE_CARD_DIR, f"{member.id}_profile.png")
        card.save(output_path, optimize=True)
        return output_path

    @commands.command(name="profile")
    async def profile(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author

        stats = load_stats()
        entry = get_user_stats(stats, member.id)
        unlocked = [key for key in entry.get("badges", []) if key in BADGES]

        card_path = await self.build_profile_card(member, entry, unlocked)
        if card_path and os.path.isfile(card_path):
            file = discord.File(card_path, filename="profile_card.png")
            embed = discord.Embed(color=discord.Color.green())
            embed.set_image(url="attachment://profile_card.png")
            await ctx.send(embed=embed, file=file)
            return

        # Fallback
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
                f"Best !work gain: **{max_gain:,}**\n"
                f"Unlocked badges: **{len(unlocked)}** (use `!mybadges`)"
            ),
        )
        await ctx.send(embed=embed)

    @commands.command(name="mybadges", aliases=["profilebadges"])
    async def mybadges(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author

        stats = load_stats()
        entry = get_user_stats(stats, member.id)
        unlocked_keys = [key for key in entry.get("badges", []) if key in BADGES]
        badge_items = [(key, BADGES[key]) for key in unlocked_keys]

        view = UnlockedBadgesPaginationView(ctx.author.id, member, badge_items)
        message = await ctx.send(embed=view.build_embed(), view=view)
        view.message = message

    @commands.command(name="badges")
    async def badges(self, ctx):
        badge_items = list(BADGES.items())
        if not badge_items:
            return await ctx.send("No badges configured.")

        view = BadgeGuidePaginationView(ctx.author.id, badge_items)
        message = await ctx.send(embed=view.build_embed(), view=view)
        view.message = message


async def setup(bot):
    await bot.add_cog(ProfileCog(bot))

