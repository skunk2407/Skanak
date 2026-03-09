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
            r = int(28 + (98 - 28) * t)
            g = int(18 + (42 - 18) * t)
            b = int(30 + (72 - 30) * t)
            draw.line([(0, y), (w, y)], fill=(r, g, b, 255))

    def _draw_cheese_icon(self, draw: ImageDraw.ImageDraw, x: int, y: int, scale: int = 1):
        w = 40 * scale
        h = 28 * scale
        color_main = (255, 206, 89, 255)
        color_shadow = (230, 156, 52, 255)
        draw.polygon(
            [
                (x, y + h),
                (x + int(0.15 * w), y + int(0.15 * h)),
                (x + w, y + int(0.05 * h)),
                (x + int(0.85 * w), y + h),
            ],
            fill=color_main,
            outline=color_shadow,
        )
        holes = [
            (int(0.25 * w), int(0.35 * h), int(0.12 * w)),
            (int(0.58 * w), int(0.42 * h), int(0.10 * w)),
            (int(0.48 * w), int(0.70 * h), int(0.08 * w)),
        ]
        for hx, hy, hr in holes:
            draw.ellipse((x + hx - hr, y + hy - hr, x + hx + hr, y + hy + hr), fill=(245, 170, 70, 255))

    async def build_profile_card(self, member: discord.Member, entry: dict, badge_keys: List[str]) -> Optional[str]:
        # Tall card so Discord renders it bigger in chat.
        width, height = 900, 980
        card = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        self._draw_gradient(card)
        draw = ImageDraw.Draw(card)

        # Main panel and header bar
        draw.rounded_rectangle((26, 24, width - 26, height - 24), radius=28, fill=(23, 27, 40, 242))
        draw.rounded_rectangle((44, 42, width - 44, height - 42), radius=22, fill=(32, 36, 52, 230))
        draw.rounded_rectangle((44, 42, width - 44, 280), radius=22, fill=(255, 176, 66, 230))
        draw.rectangle((44, 160, width - 44, 280), fill=(255, 140, 52, 220))

        # Decorative cheese icons
        self._draw_cheese_icon(draw, 700, 86, scale=2)
        self._draw_cheese_icon(draw, 760, 210, scale=1)
        self._draw_cheese_icon(draw, 52, 52, scale=1)

        title_font = self._load_font(56, bold=True)
        subtitle_font = self._load_font(25, bold=False)
        label_font = self._load_font(30, bold=False)
        value_font = self._load_font(34, bold=True)
        badge_label_font = self._load_font(28, bold=True)
        hint_font = self._load_font(22, bold=False)

        # Avatar
        avatar_img = None
        try:
            avatar_bytes = await member.display_avatar.with_size(256).read()
            avatar_img = Image.open(BytesIO(avatar_bytes))
        except Exception:
            avatar_img = None

        if avatar_img is not None:
            self._paste_circular_avatar(card, avatar_img, x=78, y=74, size=180)
            draw.ellipse((78, 74, 258, 254), outline=(255, 248, 217, 255), width=6)

        # Header text
        draw.text((280, 82), member.display_name, font=title_font, fill=(34, 26, 20, 255))
        draw.text((282, 150), "CHEESE ECONOMY PROFILE", font=subtitle_font, fill=(78, 34, 15, 255))

        cheese = int(entry.get("cheese", 0))
        max_cheese = int(entry.get("max_cheese", cheese))
        purchases = int(entry.get("shop_purchases", 0))
        max_gain = int(entry.get("max_work_gain", 0))

        # Stat cards (2x2)
        stats = [
            ("Cheese Balance", f"{cheese:,}"),
            ("All-time Max", f"{max_cheese:,}"),
            ("Items Bought", f"{purchases:,}"),
            ("Best !work Gain", f"{max_gain:,}"),
        ]
        stat_boxes = [
            (70, 320, 410, 430),
            (490, 320, 830, 430),
            (70, 455, 410, 565),
            (490, 455, 830, 565),
        ]
        for (label, value), box in zip(stats, stat_boxes):
            x1, y1, x2, y2 = box
            draw.rounded_rectangle(box, radius=18, fill=(49, 57, 80, 235), outline=(255, 171, 79, 255), width=3)
            draw.text((x1 + 20, y1 + 16), label, font=label_font, fill=(227, 233, 245, 255))
            draw.text((x1 + 20, y1 + 58), value, font=value_font, fill=(255, 219, 120, 255))

        # Badge preview (clean grid)
        draw.text((70, 620), "Badge Preview", font=badge_label_font, fill=(255, 233, 177, 255))
        badge_paths = self._existing_badge_images(badge_keys)
        preview_count = 8
        shown = badge_paths[:preview_count]
        badge_x = 90
        badge_y = 664
        badge_size = 76
        badge_gap_x = 20
        badge_gap_y = 18

        if shown:
            for i, path in enumerate(shown):
                try:
                    badge = Image.open(path).convert("RGBA")
                    badge = ImageOps.contain(badge, (badge_size, badge_size), Image.Resampling.LANCZOS)
                    col = i % 4
                    row = i // 4
                    slot_x = badge_x + col * (badge_size + badge_gap_x)
                    slot_y = badge_y + row * (badge_size + badge_gap_y)
                    draw.rounded_rectangle(
                        (slot_x - 8, slot_y - 8, slot_x + badge_size + 8, slot_y + badge_size + 8),
                        radius=12,
                        fill=(43, 50, 72, 240),
                        outline=(255, 186, 84, 255),
                        width=2,
                    )
                    card.paste(badge, (slot_x, slot_y), badge)
                except Exception:
                    continue
        else:
            draw.text((90, 690), "No badges unlocked yet.", font=hint_font, fill=(172, 186, 208, 255))

        remaining = max(0, len(badge_paths) - preview_count)
        info_x = 520
        info_y = 700
        draw.rounded_rectangle((info_x, info_y, 820, 840), radius=18, fill=(46, 54, 77, 240), outline=(131, 215, 255, 255), width=2)
        draw.text((info_x + 18, info_y + 20), f"Unlocked: {len(badge_paths)}", font=label_font, fill=(226, 235, 251, 255))
        if remaining > 0:
            draw.text(
                (info_x + 18, info_y + 60),
                f"+{remaining} more badges",
                font=hint_font,
                fill=(146, 216, 255, 255),
            )
        draw.text(
            (info_x + 18, info_y + 98),
            "Use !mybadges",
            font=hint_font,
            fill=(146, 216, 255, 255),
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
