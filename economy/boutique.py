import math
from datetime import datetime
from typing import Dict, List, Optional

import discord
from discord.ext import commands

from economy.badges import BADGES, award_badge
from economy.stats import get_user_stats, load_stats, save_stats
from storage.database import load_app_state, save_app_state

# Shop data
shop_items = [
    # Roles
    {"code": "01", "name": "Wealthy Wacko [VIP]", "price": 100000, "id": 852474925914259476},
    {"code": "02", "name": "Customized Color Role", "price": 110000, "id": 1309867587240329327},
    {"code": "03", "name": "Customized Badge Role", "price": 110000, "id": 1309867842237235232},
    # Shields
    {"code": "11", "name": "Safe Mode 12h", "price": 200, "shield_duration": 12 * 3600},
    {"code": "12", "name": "Safe Mode 7d", "price": 3400, "shield_duration": 7 * 24 * 3600},
    {"code": "13", "name": "Safe Mode Lifetime", "price": 100000, "shield_permanent": True},
    # Boosters
    {"code": "21", "name": "Double Work Ticket", "price": 100, "multiplier_type": "work", "multiplier": 2.0},
    {"code": "22", "name": "Double Daily Ticket", "price": 100, "multiplier_type": "daily", "multiplier": 2.0},
    {"code": "23", "name": "Steal Booster", "price": 150, "steal_boost": 0.5},
    # Special
    {"code": "31", "name": "Trap Cheese", "price": 1200, "trap_cheese": True},
    {"code": "32", "name": "Counter Steal", "price": 1800, "counter_steal": True},
    {"code": "41", "name": "Cheese Bomb", "price": 10000, "bomb_amount": 30, "bomb_cap": 200},
    {"code": "51", "name": "Lottery Ticket", "price": 500, "lottery_ticket": True},
    {"code": "61", "name": "Rename Someone (24h)", "price": 2500, "rename_power": True},
]

locked_items = [
    {"code": "90", "name": "Certified Cheese Enjoyer", "description": "Locked - Obtain via !cheese (0.1% chance)"}
]

ITEMS_PER_PAGE = 5

CATEGORY_META = {
    "roles": {"title": "Roles", "emoji": "🎖️", "color": discord.Color.purple()},
    "shields": {"title": "Shields", "emoji": "🛡️", "color": discord.Color.blue()},
    "boosters": {"title": "Boosters", "emoji": "⚡", "color": discord.Color.orange()},
    "special": {"title": "Special", "emoji": "🧪", "color": discord.Color.teal()},
    "exclusive": {"title": "Exclusive", "emoji": "🔒", "color": discord.Color.dark_gold()},
}


def _build_category_map() -> Dict[str, List[dict]]:
    roles, shields, boosters, special = [], [], [], []
    for item in shop_items:
        if "id" in item:
            roles.append(item)
            continue
        if item.get("shield_permanent") or "shield_duration" in item:
            shields.append(item)
            continue
        if item.get("multiplier_type") or item.get("steal_boost"):
            boosters.append(item)
            continue
        special.append(item)
    return {
        "roles": roles,
        "shields": shields,
        "boosters": boosters,
        "special": special,
        "exclusive": locked_items,
    }


def _format_item(item: dict, category: str) -> str:
    if category == "exclusive":
        return f"`#{item['code']}` **{item['name']}**\n{item.get('description', '-')}"

    price = f"{int(item['price']):,} 🧀"
    details = ""
    if item.get("shield_permanent"):
        details = "Permanent shield"
    elif "shield_duration" in item:
        hours = int(item["shield_duration"]) // 3600
        details = f"Shield for {hours}h"
    elif item.get("multiplier_type") == "work":
        details = f"Next !work x{item['multiplier']}"
    elif item.get("multiplier_type") == "daily":
        details = f"Next !daily x{item['multiplier']}"
    elif item.get("steal_boost"):
        details = f"Next !steal +{int(item['steal_boost'] * 100)}%"
    elif item.get("trap_cheese"):
        details = "Anti-steal trap (1 charge)"
    elif item.get("counter_steal"):
        details = "Auto counter-steal (1 charge)"
    elif item.get("bomb_amount"):
        details = f"Gives {item['bomb_amount']} 🧀 to up to {item.get('bomb_cap', 200)} members"
    elif item.get("lottery_ticket"):
        details = "Entry ticket for lottery draw"
    elif item.get("rename_power"):
        details = "1 rename token (24h)"
    elif "id" in item:
        details = "Unlocks server role"

    return f"`#{item['code']}` **{item['name']}** - **{price}**\n{details}"


class ShopMenuView(discord.ui.View):
    def __init__(self, author_id: int, balance: int):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.balance = balance
        self.current_category = "home"
        self.page = 0
        self.message: Optional[discord.Message] = None
        self.categories = _build_category_map()
        self._refresh_buttons()

    def _max_pages(self) -> int:
        if self.current_category == "home":
            return 1
        total = len(self.categories.get(self.current_category, []))
        return max(1, math.ceil(total / ITEMS_PER_PAGE))

    def _refresh_buttons(self):
        is_home = self.current_category == "home"
        max_pages = self._max_pages()
        self.prev_btn.disabled = is_home or self.page <= 0
        self.next_btn.disabled = is_home or self.page >= max_pages - 1
        self.home_btn.disabled = is_home

        self.roles_btn.style = discord.ButtonStyle.primary if self.current_category == "roles" else discord.ButtonStyle.secondary
        self.shields_btn.style = discord.ButtonStyle.primary if self.current_category == "shields" else discord.ButtonStyle.secondary
        self.boosters_btn.style = discord.ButtonStyle.primary if self.current_category == "boosters" else discord.ButtonStyle.secondary
        self.special_btn.style = discord.ButtonStyle.primary if self.current_category == "special" else discord.ButtonStyle.secondary
        self.exclusive_btn.style = discord.ButtonStyle.primary if self.current_category == "exclusive" else discord.ButtonStyle.secondary

    def _home_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🧀 TF Corporation Shop",
            description=(
                "Browse by category using the buttons below.\n"
                "Buy with `!buy #code` or `!buy <item name>`."
            ),
            color=discord.Color.gold(),
        )
        embed.add_field(name="🎖️ Roles", value=f"{len(self.categories['roles'])} items", inline=True)
        embed.add_field(name="🛡️ Shields", value=f"{len(self.categories['shields'])} items", inline=True)
        embed.add_field(name="⚡ Boosters", value=f"{len(self.categories['boosters'])} items", inline=True)
        embed.add_field(name="🧪 Special", value=f"{len(self.categories['special'])} items", inline=True)
        embed.add_field(name="🔒 Exclusive", value=f"{len(self.categories['exclusive'])} items", inline=True)
        embed.add_field(
            name="Quick Tips",
            value="Use `!inventory` to check active effects.\nUse `!lottery` to view ticket pot.",
            inline=False,
        )
        embed.set_footer(text=f"Your balance: {self.balance:,} 🧀")
        return embed

    def _category_embed(self) -> discord.Embed:
        meta = CATEGORY_META[self.current_category]
        title = f"{meta['emoji']} Shop - {meta['title']}"
        entries = self.categories.get(self.current_category, [])
        max_pages = self._max_pages()
        start = self.page * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        page_entries = entries[start:end]

        embed = discord.Embed(
            title=title,
            description="Use `!buy #code` to purchase an item.",
            color=meta["color"],
        )
        if not page_entries:
            embed.add_field(name="No items", value="Nothing available in this category.", inline=False)
        else:
            for item in page_entries:
                embed.add_field(
                    name=f"#{item['code']} - {item['name']}",
                    value=_format_item(item, self.current_category),
                    inline=False,
                )
        embed.set_footer(text=f"Page {self.page + 1}/{max_pages} | Balance: {self.balance:,} 🧀")
        return embed

    def build_embed(self) -> discord.Embed:
        if self.current_category == "home":
            return self._home_embed()
        return self._category_embed()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the command author can control this shop panel.", ephemeral=True)
            return False
        return True

    async def _switch_category(self, interaction: discord.Interaction, category: str):
        self.current_category = category
        self.page = 0
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Roles", style=discord.ButtonStyle.secondary, row=0)
    async def roles_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._switch_category(interaction, "roles")

    @discord.ui.button(label="Shields", style=discord.ButtonStyle.secondary, row=0)
    async def shields_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._switch_category(interaction, "shields")

    @discord.ui.button(label="Boosters", style=discord.ButtonStyle.secondary, row=0)
    async def boosters_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._switch_category(interaction, "boosters")

    @discord.ui.button(label="Special", style=discord.ButtonStyle.secondary, row=0)
    async def special_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._switch_category(interaction, "special")

    @discord.ui.button(label="Exclusive", style=discord.ButtonStyle.secondary, row=0)
    async def exclusive_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._switch_category(interaction, "exclusive")

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary, row=1)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Home", style=discord.ButtonStyle.success, row=1)
    async def home_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._switch_category(interaction, "home")

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, row=1)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = min(self._max_pages() - 1, self.page + 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


class Shop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="shop")
    async def shop(self, ctx: commands.Context):
        """Open interactive shop menu with category buttons."""
        stats = load_stats()
        user = get_user_stats(stats, ctx.author.id)
        balance = int(user.get("cheese", 0))
        view = ShopMenuView(author_id=ctx.author.id, balance=balance)
        message = await ctx.send(embed=view.build_embed(), view=view)
        view.message = message

    @commands.command(name="buy")
    async def buy(self, ctx: commands.Context, *, item_query: str):
        """Buy an item by code or name."""
        stats = load_stats()
        user = get_user_stats(stats, ctx.author.id)

        # Lookup item
        key = item_query.strip()
        code = key.lstrip("#").upper()
        item = next((i for i in shop_items if i["code"] == code), None)
        if not item:
            item = next((i for i in shop_items if i["name"].lower() == key.lower()), None)
        if not item:
            if any(i["code"] == code for i in locked_items) or any(i["name"].lower() == key.lower() for i in locked_items):
                return await ctx.send("❌ This item is locked. Obtain via `!cheese`.")
            return await ctx.send("❌ Item not found. Check `!shop` for valid codes/names.")

        price = item["price"]
        now_ts = datetime.utcnow().timestamp()

        # Pre-purchase checks
        if item.get("shield_duration") and user.get("safe_mode_expiry", 0) > now_ts:
            return await ctx.send("❌ You already have an active shield.")
        if item.get("shield_permanent") and user.get("safe_mode_permanent"):
            return await ctx.send("❌ You already own a permanent shield.")
        if item.get("multiplier_type") == "work" and user.get("next_work_multiplier", 1.0) > 1.0:
            return await ctx.send("❌ Your next work is already boosted.")
        if item.get("multiplier_type") == "daily" and user.get("next_daily_multiplier", 1.0) > 1.0:
            return await ctx.send("❌ Your next daily is already boosted.")
        if item.get("steal_boost") and user.get("steal_boost", 0.0) > 0.0:
            return await ctx.send("❌ Your next steal is already boosted.")
        if item.get("id") and item["id"] in user.get("roles", []):
            return await ctx.send("❌ You already own this role.")
        if user["cheese"] < price:
            return await ctx.send("❌ You don't have enough cheese.")

        # Transaction
        user["cheese"] -= price
        user["shop_purchases"] = user.get("shop_purchases", 0) + 1
        user["spent_in_shop"] = True
        user["cheese_since_last_spend"] = 0

        # Apply effect
        msg = None
        if item.get("shield_permanent"):
            user["safe_mode_permanent"] = True
            msg = "✅ Permanent shield activated!"

        elif "shield_duration" in item:
            user["safe_mode_expiry"] = now_ts + int(item["shield_duration"])
            hrs = item["shield_duration"] // 3600
            msg = f"✅ Shield active for {hrs}h!"

        elif item.get("multiplier_type") == "work":
            user["next_work_multiplier"] = item["multiplier"]
            msg = f"✅ Next `!work` reward x{item['multiplier']}!"

        elif item.get("multiplier_type") == "daily":
            user["next_daily_multiplier"] = item["multiplier"]
            msg = f"✅ Next `!daily` reward x{item['multiplier']}!"

        elif item.get("steal_boost"):
            user["steal_boost"] = item["steal_boost"]
            pct = int(item["steal_boost"] * 100)
            msg = f"✅ Next `!steal` boosted by +{pct}%!"

        elif item.get("trap_cheese"):
            user["trap_cheese_charges"] = user.get("trap_cheese_charges", 0) + 1
            msg = "🧨 Trap armed! It will trigger on the next steal attempt against you."

        elif item.get("counter_steal"):
            user["counter_steal_charges"] = user.get("counter_steal_charges", 0) + 1
            msg = "🔄 Counter-Steal ready! If a steal succeeds against you, it will auto retaliate."

        elif item.get("bomb_amount"):
            amount_each = int(item["bomb_amount"])
            cap = int(item.get("bomb_cap", 200))
            credited = 0
            guild = ctx.guild
            members = []

            if guild:
                for uid in list(stats.keys()):
                    m = guild.get_member(int(uid))
                    if m and not m.bot:
                        members.append(m)
                        if len(members) >= cap:
                            break
                if len(members) < cap:
                    for m in guild.members:
                        if not m.bot and m not in members:
                            members.append(m)
                            if len(members) >= cap:
                                break

            for m in members:
                entry = get_user_stats(stats, m.id)
                entry["cheese"] = entry.get("cheese", 0) + amount_each
                credited += 1

            msg = f"💥 Cheese Bomb exploded! Gave **{amount_each} 🧀** to **{credited}** members."

        elif item.get("lottery_ticket"):
            lotto = load_app_state("economy.lottery", default={})
            if not isinstance(lotto, dict):
                lotto = {}
            gid = str(ctx.guild.id) if ctx.guild else "global"
            lotto.setdefault(gid, []).append(str(ctx.author.id))
            save_app_state("economy.lottery", lotto)
            msg = "🎟️ Ticket purchased! Good luck for the next draw."

        elif item.get("rename_power"):
            user["rename_tokens"] = user.get("rename_tokens", 0) + 1
            msg = "✏️ Rename token acquired! Use `!rename @member NewNickname` (24h)."

        else:
            role = discord.utils.get(ctx.guild.roles, id=item["id"]) if ctx.guild else None
            if role:
                try:
                    await ctx.author.add_roles(role, reason="Shop purchase")
                    user["roles"].append(item["id"])
                    msg = f"✅ You purchased **{item['name']}** and got the role!"
                except discord.Forbidden:
                    msg = "❌ I don't have permission to add that role."
            else:
                msg = "❌ Role not found on this server."

        save_stats(stats)
        await ctx.send(msg)

        # Purchase badges
        cnt = user["shop_purchases"]
        if cnt == 10 and award_badge(ctx.author.id, "shop_veteran"):
            info = BADGES["shop_veteran"]
            embed = discord.Embed(
                title="🎉 New Badge Unlocked!",
                description=f"{ctx.author.mention}, you earned **{info['name']}**!",
                color=discord.Color.gold(),
            )
            embed.set_thumbnail(url=info["url"])
            await ctx.send(embed=embed)
        elif cnt == 100 and award_badge(ctx.author.id, "shop_legend"):
            info = BADGES["shop_legend"]
            embed = discord.Embed(
                title="🎉 New Badge Unlocked!",
                description=f"{ctx.author.mention}, you earned **{info['name']}**!",
                color=discord.Color.gold(),
            )
            embed.set_thumbnail(url=info["url"])
            await ctx.send(embed=embed)

    @buy.error
    async def buy_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Usage: `!buy <code>` or `!buy <item name>`. Check `!shop`.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Shop(bot))

