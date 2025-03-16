import discord
from discord.ext import commands
import random
import json
import os
from datetime import datetime

class UserStats:
    def __init__(self, user_id):
        self.user_id = str(user_id)
        self.cheese = 0
        self.last_work = None
        self.last_daily = None
        self.daily_streak = 0

    def to_dict(self):
        return {
            'cheese': self.cheese,
            'last_work': self.last_work,
            'last_daily': self.last_daily,
            'daily_streak': self.daily_streak,
        }

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stats_file = '/home/container/Skanak/economy/user_stats.json'
        self.cooldown_time = 7200
        self.daily_cooldown = 86400

        if not os.path.exists(self.stats_file):
            with open(self.stats_file, 'w') as f:
                json.dump({}, f)

    def load_stats(self):
        with open(self.stats_file, 'r') as f:
            return json.load(f)

    def save_stats(self, stats):
        with open(self.stats_file, 'w') as f:
            json.dump(stats, f, indent=4)

    def get_user_stats(self, user_id):
        stats = self.load_stats()
        if str(user_id) not in stats:
            user_stats = UserStats(user_id)
            stats[str(user_id)] = user_stats.to_dict()
        return stats[str(user_id)], stats

    @commands.command(name='work')
    async def work(self, ctx):
        user_id = ctx.author.id
        user_stats, stats = self.get_user_stats(user_id)

        last_work = user_stats['last_work']
        now = datetime.utcnow()

        if last_work:
            last_work_time = datetime.strptime(last_work, '%Y-%m-%d %H:%M:%S.%f')
            cooldown_remaining = self.cooldown_time - (now - last_work_time).total_seconds()

            if cooldown_remaining > 0:
                await ctx.send(f"⏳ You need to wait another {int(cooldown_remaining // 60)} minutes before you can work again.")
                return

        reward = random.randint(0, 350)
        user_stats['cheese'] += reward
        user_stats['last_work'] = str(now)

        if reward == 0:
            await ctx.send(f"😞 {ctx.author.mention}, you caught something useless... You got rotten cheese instead!")
        elif reward < 100:
            await ctx.send(f"💼 {ctx.author.mention}, you earned {reward} 🧀. Not bad, but you can do better!")
        elif reward < 250:
            await ctx.send(f"🎉 {ctx.author.mention}, you earned {reward} 🧀! Good job!")
        else:
            await ctx.send(f"🚀 Wow! {ctx.author.mention}, you earned {reward} 🧀! That's amazing!")

        self.save_stats(stats)

    @commands.command(name='daily')
    async def daily(self, ctx):
        user_id = ctx.author.id
        user_stats, stats = self.get_user_stats(user_id)

        last_daily = user_stats['last_daily']
        now = datetime.utcnow()

        if last_daily:
            last_daily_time = datetime.strptime(last_daily, '%Y-%m-%d %H:%M:%S.%f')
            if (now - last_daily_time).days > 1:
                user_stats['daily_streak'] = 0
            elif (now - last_daily_time).total_seconds() < self.daily_cooldown:
                remaining_time = self.daily_cooldown - (now - last_daily_time).total_seconds()
                await ctx.send(f"⏳ You need to wait {int(remaining_time // 3600)} more hours before claiming your daily reward.")
                return

        if user_stats['daily_streak'] < 30:
            reward = 100 + (user_stats['daily_streak'] * 25)
            user_stats['daily_streak'] += 1
        else:
            reward = 100
            user_stats['daily_streak'] = 1

        user_stats['cheese'] += reward
        user_stats['last_daily'] = str(now)

        await ctx.send(f"🎉 {ctx.author.mention}, you have claimed your daily reward of {reward} 🧀!")
        self.save_stats(stats)

    @commands.command(name='balance')
    async def balance(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author  # Si aucun membre n'est mentionné, utilise l'auteur de la commande

        stats = self.load_stats()  # Charge les statistiques depuis le fichier JSON

        if str(member.id) in stats:
            cheese = stats[str(member.id)]['cheese']
            await ctx.send(f"💰 {member.mention} has {cheese} 🧀.")
        else:
            await ctx.send(f"No information found for {member.mention}.")

async def setup(bot):
    await bot.add_cog(Economy(bot))
