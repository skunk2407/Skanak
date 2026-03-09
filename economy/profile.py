import os
from typing import List, Optional, Tuple

import discord
from discord.ext import commands
from PIL import Image

from economy.badges import BADGES
from economy.stats import get_user_stats, load_stats

BASE_DIR = os.path.dirname(__file__)
BADGES_DIR = os.path.join(BASE_DIR, "badges", "images", "resized")
SPRITE_DIR = os.path.join(BASE_DIR, "badges", "images", "sprite")
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
            title="🏅 Badge Guide",
            description="Here is how to unlock each badge:",
            color=discord.Color.blue(),
        )

        for _, info in self._current_slice():
            embed.add_field(
                name=info.get("name", "Unknown badge"),
                value=info.get("description", "—"),
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

    def build_badges_sprite(self, badge_keys: List[str], user_id: str) -> Optional[str]:
        paths = self._existing_badge_images(badge_keys)
        if not paths:
            return None

        images = [Image.open(path).convert("RGBA") for path in paths]
        total_width = sum(img.width for img in images)
        max_height = max(img.height for img in images)
        sprite = Image.new("RGBA", (total_width, max_height), (0, 0, 0, 0))

        x = 0
        for img in images:
            sprite.paste(img, (x, 0), img)
            x += img.width

        os.makedirs(SPRITE_DIR, exist_ok=True)
        output_path = os.path.join(SPRITE_DIR, f"{user_id}_badges.png")
        try:
            sprite.save(output_path, optimize=True)
        finally:
            for img in images:
                img.close()
        return output_path

    @commands.command(name="profile")
    async def profile(self, ctx, member: discord.Member = None):
        """
        Show one member profile:
        - cheese balance
        - all-time max balance
        - best single !work gain
        - unlocked badges
        - total shop purchases
        """
        if member is None:
            member = ctx.author

        stats = load_stats()
        entry = get_user_stats(stats, member.id)
        badges = entry.get("badges", [])
        purchases = int(entry.get("shop_purchases", 0))
        max_gain = int(entry.get("max_work_gain", 0))
        max_cheese = int(entry.get("max_cheese", entry.get("cheese", 0)))

        embed = discord.Embed(
            title=f"{member.display_name}'s Profile",
            color=discord.Color.green(),
        )
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)

        embed.description = (
            f"🧀 Cheese Balance: **{entry.get('cheese', 0):,}**\n"
            f"🏔️ All-time Max Cheese: **{max_cheese:,}** 🧀\n"
            f"🛍️ Total Items Bought: **{purchases}**\n"
            f"🔝 Best !work gain: **{max_gain:,}** 🧀"
        )

        if badges:
            known = [b for b in badges if b in BADGES]
            if known:
                embed.add_field(
                    name="🏅 Badges",
                    value="Your unlocked badges are shown below 👇",
                    inline=False,
                )
                sprite_path = self.build_badges_sprite(known, str(member.id))
                if sprite_path:
                    file = discord.File(sprite_path, filename="badges.png")
                    embed.set_image(url="attachment://badges.png")
                    await ctx.send(embed=embed, file=file)
                    return

        if not badges:
            embed.add_field(name="🏅 Badges", value="None yet!", inline=False)
        else:
            embed.add_field(name="🏅 Badges", value="(No local images found for your badges)", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="badges")
    async def badges(self, ctx):
        """List all badges and their unlock conditions with pagination."""
        badge_items = list(BADGES.items())
        if not badge_items:
            return await ctx.send("No badges configured.")

        view = BadgePaginationView(ctx.author.id, badge_items)
        message = await ctx.send(embed=view.build_embed(), view=view)
        view.message = message


async def setup(bot):
    await bot.add_cog(ProfileCog(bot))
