import os
import json
from datetime import datetime

import discord
from discord.ext import commands

from economy.stats import load_stats, save_stats, get_user_stats
from economy.badges import award_badge, BADGES

# === Items de base ===
shop_items = [
    # Roles
    {'code': '01', 'name': '💸 Wealthy Wacko [VIP]',  'price': 100000, 'id': 852474925914259476},
    {'code': '02', 'name': 'CUSTOMIZED COLOR ROLE',   'price': 110000, 'id': 1309867587240329327},
    {'code': '03', 'name': 'CUSTOMIZED BADGE ROLE',   'price': 110000, 'id': 1309867842237235232},
    # Shields
    {'code': '11', 'name': 'Safe Mode 12h',           'price': 200,    'shield_duration': 12 * 3600},
    {'code': '12', 'name': 'Safe Mode 7d',            'price': 3400,   'shield_duration': 7 * 24 * 3600},
    {'code': '13', 'name': 'Safe Mode Lifetime',      'price': 100000, 'shield_permanent': True},
    # Boosters
    {'code': '21', 'name': 'Double Work Ticket',      'price': 100,    'multiplier_type': 'work',  'multiplier': 2.0},
    {'code': '22', 'name': 'Double Daily Ticket',     'price': 100,    'multiplier_type': 'daily', 'multiplier': 2.0},
    {'code': '23', 'name': 'Steal Booster',           'price': 150,    'steal_boost': 0.5},
]

locked_items = [
    {'code': '90', 'name': 'CERTIFIED CHEESE ENJOYER', 'description': 'Locked — Obtain via `!cheese` (0.1% chance)'}
]

# === Nouveaux items “utiles” ===
extra_items = [
    {'code': '31', 'name': 'Trap Cheese',              'price': 1200,  'trap_cheese': True},                  # 1 charge anti-steal
    {'code': '32', 'name': 'Counter Steal',            'price': 1800,  'counter_steal': True},                # 1 charge contre-vol
    {'code': '41', 'name': 'Cheese Bomb',              'price': 10000, 'bomb_amount': 30, 'bomb_cap': 200},   # +30🧀 à 200 membres max
    {'code': '51', 'name': 'Lottery Ticket',           'price': 500,   'lottery_ticket': True},               # entrée tirage
    {'code': '61', 'name': 'Rename Someone (24h)',     'price': 2500,  'rename_power': True},                 # 1 token rename
]

# Concatène
shop_items = shop_items + extra_items


class Shop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.leaderboard_file = os.path.join(os.path.dirname(__file__), "cheese_leaderboard.json")
        if not os.path.exists(self.leaderboard_file):
            with open(self.leaderboard_file, 'w') as f:
                json.dump([], f)

    @commands.command(name='shop')
    async def shop(self, ctx: commands.Context):
        """🛍️ Show the shop with item codes for easy purchase."""
        embed = discord.Embed(
            title="🧀 TF Corporation Shop",
            description="Use `!buy <code>` or `!buy <item name>` to purchase.",
            color=0xDAF7A6
        )
        if ctx.guild and ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        # Roles
        roles = [
            f"`#{i['code']}` **{i['name']}** — {i['price']:,} 🧀"
            for i in shop_items
            if 'id' in i and not i.get('shield_duration') and not i.get('multiplier_type') and not i.get('steal_boost')
        ]
        embed.add_field(name="🎖️ Roles", value="\n".join(roles) or "No roles.", inline=False)

        # Shields
        shields = []
        for i in shop_items:
            if i.get('shield_permanent') or 'shield_duration' in i:
                code, name, price = i['code'], i['name'], f"{i['price']:,} 🧀"
                if i.get('shield_permanent'):
                    desc = "(Permanent Shield) 🛡️"
                else:
                    hrs = i['shield_duration'] // 3600
                    desc = f"({hrs}h Shield) 🛡️"
                shields.append(f"`#{code}` **{name}** — {price} {desc}")
        embed.add_field(name="🛡️ Shields", value="\n".join(shields) or "No shields.", inline=False)

        # Boosters
        boosts = []
        for i in shop_items:
            if i.get('multiplier_type') == 'work':
                boosts.append(f"`#{i['code']}` **{i['name']}** — {i['price']:,} 🧀 (Next `!work` ×{i['multiplier']}) ⚡")
            elif i.get('multiplier_type') == 'daily':
                boosts.append(f"`#{i['code']}` **{i['name']}** — {i['price']:,} 🧀 (Next `!daily` ×{i['multiplier']}) ⚡")
            elif i.get('steal_boost'):
                pct = int(i['steal_boost'] * 100)
                boosts.append(f"`#{i['code']}` **{i['name']}** — {i['price']:,} 🧀 (+{pct}% Next `!steal`) ⚔️")
        embed.add_field(name="⚡ Boosters", value="\n".join(boosts) or "No boosters.", inline=False)

        # Special
        specials = []
        for i in extra_items:
            if i.get('trap_cheese'):
                specials.append(f"`#{i['code']}` **{i['name']}** — {i['price']:,} 🧀 (Anti-steal trap, 1 charge)")
            elif i.get('counter_steal'):
                specials.append(f"`#{i['code']}` **{i['name']}** — {i['price']:,} 🧀 (Auto counter-steal, 1 charge)")
            elif i.get('bomb_amount'):
                specials.append(f"`#{i['code']}` **{i['name']}** — {i['price']:,} 🧀 (Gives {i['bomb_amount']} 🧀 to up to {i.get('bomb_cap',200)} members)")
            elif i.get('lottery_ticket'):
                specials.append(f"`#{i['code']}` **{i['name']}** — {i['price']:,} 🧀 (Join the lottery pot)")
            elif i.get('rename_power'):
                specials.append(f"`#{i['code']}` **{i['name']}** — {i['price']:,} 🧀 (1 rename token, 24h)")
        if specials:
            embed.add_field(name="🧪 Special", value="\n".join(specials), inline=False)

        # Exclusive
        locked = [f"`#{i['code']}` **{i['name']}** — {i['description']}" for i in locked_items]
        embed.add_field(name="🔒 Exclusive", value="\n".join(locked), inline=False)

        await ctx.send(embed=embed)

    @commands.command(name='buy')
    async def buy(self, ctx: commands.Context, *, item_query: str):
        """💸 Buy an item by code or name."""
        stats = load_stats()
        user = get_user_stats(stats, ctx.author.id)

        # Lookup item
        key  = item_query.strip()
        code = key.lstrip('#').upper()
        item = next((i for i in shop_items if i['code'] == code), None)
        if not item:
            item = next((i for i in shop_items if i['name'].lower() == key.lower()), None)
        if not item:
            if any(i['code'] == code for i in locked_items) or any(i['name'].lower() == key.lower() for i in locked_items):
                return await ctx.send("❌ This item is locked. Obtain via `!cheese`.")
            return await ctx.send("❌ Item not found. Check `!shop` for valid codes/names.")

        price  = item['price']
        now_ts = datetime.utcnow().timestamp()

        # Pre-purchase checks
        if item.get('shield_duration') and user.get('safe_mode_expiry', 0) > now_ts:
            return await ctx.send("❌ You already have an active shield.")
        if item.get('shield_permanent') and user.get('safe_mode_permanent'):
            return await ctx.send("❌ You already own a permanent shield.")
        if item.get('multiplier_type') == 'work' and user.get('next_work_multiplier', 1.0) > 1.0:
            return await ctx.send("❌ Your next work is already boosted.")
        if item.get('multiplier_type') == 'daily' and user.get('next_daily_multiplier', 1.0) > 1.0:
            return await ctx.send("❌ Your next daily is already boosted.")
        if item.get('steal_boost') and user.get('steal_boost', 0.0) > 0.0:
            return await ctx.send("❌ Your next steal is already boosted.")
        if item.get('id') and item['id'] in user.get('roles', []):
            return await ctx.send("❌ You already own this role.")
        if user['cheese'] < price:
            return await ctx.send("❌ You don't have enough cheese.")

        # Transaction + reset hoarder-ish
        user['cheese'] -= price
        user['shop_purchases'] = user.get('shop_purchases', 0) + 1
        user['spent_in_shop'] = True
        user['cheese_since_last_spend'] = 0

        # Apply effect
        msg = None
        if item.get('shield_permanent'):
            user['safe_mode_permanent'] = True
            msg = "✅ Permanent shield activated!"

        elif 'shield_duration' in item:
            user['safe_mode_expiry'] = now_ts + int(item['shield_duration'])
            hrs = item['shield_duration'] // 3600
            msg = f"✅ Shield active for {hrs}h!"

        elif item.get('multiplier_type') == 'work':
            user['next_work_multiplier'] = item['multiplier']
            msg = f"✅ Next `!work` reward ×{item['multiplier']}!"

        elif item.get('multiplier_type') == 'daily':
            user['next_daily_multiplier'] = item['multiplier']
            msg = f"✅ Next `!daily` reward ×{item['multiplier']}!"

        elif item.get('steal_boost'):
            user['steal_boost'] = item['steal_boost']
            pct = int(item['steal_boost'] * 100)
            msg = f"✅ Next `!steal` boosted by +{pct}%!"

        elif item.get('trap_cheese'):
            user['trap_cheese_charges'] = user.get('trap_cheese_charges', 0) + 1
            msg = "🧨 Trap armed! It will trigger on the next steal attempt against you."

        elif item.get('counter_steal'):
            user['counter_steal_charges'] = user.get('counter_steal_charges', 0) + 1
            msg = "🔄 Counter-Steal ready! If a steal succeeds against you, it will auto retaliate."

        elif item.get('bomb_amount'):
            # Distribuer sans spam : jusqu’à 'bomb_cap' membres connus/actifs
            amount_each = int(item['bomb_amount'])
            cap = int(item.get('bomb_cap', 200))
            credited = 0
            guild = ctx.guild

            members = []
            if guild:
                # Priorité: membres ayant déjà des stats (actifs)
                for uid in list(stats.keys()):
                    m = guild.get_member(int(uid))
                    if m and not m.bot:
                        members.append(m)
                        if len(members) >= cap:
                            break
                # Complète avec d'autres membres si pas assez
                if len(members) < cap:
                    for m in guild.members:
                        if not m.bot and m not in members:
                            members.append(m)
                            if len(members) >= cap:
                                break

            for m in members:
                entry = get_user_stats(stats, m.id)
                entry['cheese'] = entry.get('cheese', 0) + amount_each
                credited += 1

            msg = f"💥 Cheese Bomb exploded! Gave **{amount_each} 🧀** to **{credited}** members."

        elif item.get('lottery_ticket'):
            lotto_path = os.path.join(os.path.dirname(__file__), "lottery.json")
            try:
                with open(lotto_path, "r") as f:
                    lotto = json.load(f)
            except Exception:
                lotto = {}
            gid = str(ctx.guild.id) if ctx.guild else "global"
            lotto.setdefault(gid, []).append(str(ctx.author.id))
            with open(lotto_path, "w") as f:
                json.dump(lotto, f, indent=2)
            msg = "🎟️ Ticket purchased! Good luck for the next draw."

        elif item.get('rename_power'):
            user['rename_tokens'] = user.get('rename_tokens', 0) + 1
            msg = "✏️ Rename token acquired! Use `!rename @member NewNickname` (24h)."

        else:
            # Rôle
            role = discord.utils.get(ctx.guild.roles, id=item['id']) if ctx.guild else None
            if role:
                try:
                    await ctx.author.add_roles(role, reason="Shop purchase")
                    user['roles'].append(item['id'])
                    msg = f"✅ You purchased **{item['name']}** and got the role!"
                except discord.Forbidden:
                    msg = "❌ I don't have permission to add that role."
            else:
                msg = "❌ Role not found on this server."

        # Sauvegarde & feedback
        save_stats(stats)
        await ctx.send(msg)

        # Badges d’achat (inchangés)
        cnt = user['shop_purchases']
        if cnt == 10 and award_badge(ctx.author.id, 'shop_veteran'):
            info = BADGES['shop_veteran']
            embed = discord.Embed(
                title="🎉 New Badge Unlocked!",
                description=f"{ctx.author.mention}, you earned **{info['name']}**!",
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=info['url'])
            await ctx.send(embed=embed)
        elif cnt == 100 and award_badge(ctx.author.id, 'shop_legend'):
            info = BADGES['shop_legend']
            embed = discord.Embed(
                title="🎉 New Badge Unlocked!",
                description=f"{ctx.author.mention}, you earned **{info['name']}**!",
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=info['url'])
            await ctx.send(embed=embed)

    @buy.error
    async def buy_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Usage: `!buy <code>` or `!buy <item name>`. Check `!shop`!")

async def setup(bot: commands.Bot):
    await bot.add_cog(Shop(bot))
