import discord
from discord.ext import commands
import random

# ──────────────────────────────────────────────────────────────────────────────
# 1) DICTIONNAIRE DES BANNIÈRES PAR JEU
#    Tu peux remplir ce dict avec autant de jeux que tu veux. 
#    La clé doit être EXACTEMENT le titre que l'on passe à la commande !createevent.
#    La valeur est l'URL publique de l'image de bannière (png, jpg, …).
#    Si le titre n'est pas dans ce dict, l'embed n'affichera pas d'image.
# ──────────────────────────────────────────────────────────────────────────────
GAME_BANNERS = {
    "NUCLEAR NIGHTMARE": "https://cdn.discordapp.com/attachments/1379954842985959517/1379954854457507962/nuclear-nightmare-tetiere-file-d3514fa2.png?ex=68421e9b&is=6840cd1b&hm=50c4f4012f21d862573abff7eba2a69c8af0cc10288a86c9d63dfb51bc83d6d3&",
    "REPO": "https://cdn.discordapp.com/attachments/1379954842985959517/1379955237288415353/r-e-p-o-pc-jeu-steam-cover.png?ex=68421ef6&is=6840cd76&hm=086dd780c265ae791623ccf1ea081dd2248ad0d754df94a00e1e17add8d670a4&",
    "HOLDFAST": "https://cdn.discordapp.com/attachments/1379954842985959517/1379955398219403364/holdfast-nations-at-war-high-com-781758ac-file-7817589c.png?ex=68421f1d&is=6840cd9d&hm=d4b167e1e41fcea5d792130a5418f7a778c1e22c69326130051ae27980d6c7a3&",
}


class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Stockage en mémoire de tous les events :
        # key = message_id, value = {
        #   "title": str,
        #   "date": str (YYYY-MM-DD),
        #   "emoji_map": { emoji_str: "HH:MM", ... },
        #   "participants": { emoji_str: [user_id, ...], ... }
        # }
        self.events = {}

    def build_embed(self, title: str, date: str, emoji_map: dict, participants: dict) -> discord.Embed:
        """
        Reconstruit l'embed pour l'event.
        - title       : nom de l'event (doit matcher GAME_BANNERS si tu veux une bannière)
        - date        : "YYYY-MM-DD"
        - emoji_map   : { "1️⃣": "14:00", "2️⃣": "15:00", ... } (horaires en UTC)
        - participants: { "1️⃣": [user_id, ...], ... }
        """
        # Choisir une couleur aléatoire parmi une liste (ou fixe si tu préfères)
        colors = [
            discord.Color.blurple(),
            discord.Color.dark_blue(),
            discord.Color.blue(),
            discord.Color.purple(),
            discord.Color.dark_purple()
        ]
        color = random.choice(colors)

        embed = discord.Embed(
            title=f"🎮 Event: {title}",
            description=f"📅 Date: {date}  `(all times in UTC)`",
            color=color
        )

        # Si le titre du jeu se trouve dans GAME_BANNERS, on ajoute l'image
        banner_url = GAME_BANNERS.get(title.upper())  # on standardise en majuscules
        if banner_url:
            embed.set_image(url=banner_url)

        # Pour chaque créneau, on ajoute un champ avec l'emoji, l'heure et les participants
        for emoji, hour in emoji_map.items():
            plist = participants.get(emoji, [])
            if plist:
                mentions = " ".join(f"<@{uid}>" for uid in plist)
            else:
                mentions = "_None_"
            embed.add_field(
                name=f"{emoji}  {hour} UTC",
                value=mentions,
                inline=False
            )

        # Footer / timestamp pour indiquer quand l'embed a été généré
        embed.set_footer(text="React below to join a time slot")
        embed.timestamp = discord.utils.utcnow()

        return embed

    @commands.command(name="createevent")
    async def create_event(self, ctx, title: str, date: str, *times: str):
        """
        Usage:
          !createevent "Event Title" YYYY-MM-DD HH:MM HH:MM ...

        - title : entre guillemets si tu veux des espaces (ex: "NUCLEAR NIGHTMARE")
        - date  : format ISO (YYYY-MM-DD), ex: 2025-06-06
        - times : un ou plusieurs créneaux UTC, ex: 14:00 15:00 16:00 ...
        
        Exemple concret :
          !createevent "NUCLEAR NIGHTMARE" 2025-06-06 14:00 15:00 16:00 17:00
        """
        # ─── Vérifications de base ─────────────────────────────────────────────
        if not times:
            await ctx.send(
                "❌ *You must provide at least one time slot!*\n"
                "Example:\n"
                "```!createevent \"NUCLEAR NIGHTMARE\" 2025-06-06 14:00 15:00```"
            )
            return

        if len(times) > 10:
            await ctx.send("❌ *You can propose up to 10 time slots only.*")
            return

        # On transforme le titre en majuscules pour matcher GAME_BANNERS (clé en majuscule)
        title_upper = title.upper()

        # Prépare le mapping emoji → heure, et la liste vide des participants
        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        emoji_map = {}
        participants = {}
        for i, t in enumerate(times):
            emoji = number_emojis[i]
            emoji_map[emoji] = t
            participants[emoji] = []

        # Construire et envoyer l'embed initial (sans participants)
        embed = self.build_embed(title_upper, date, emoji_map, participants)
        message = await ctx.send(embed=embed)

        # Ajouter les réactions sous l’embed
        for emoji in emoji_map.keys():
            await message.add_reaction(emoji)

        # Stocker l'event en mémoire
        self.events[message.id] = {
            "title": title_upper,
            "date": date,
            "emoji_map": emoji_map,
            "participants": participants
        }

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """
        Déclenché quand quelqu'un ajoute une réaction à n'importe quel message.
        Si c’est un message que l’on gère comme event, on met à jour l’embed.
        """
        if payload.user_id == self.bot.user.id:
            return  # Ignore les réactions du bot lui-même

        msg_id = payload.message_id
        if msg_id not in self.events:
            return  # Ce n'est pas un event que l'on gère

        emoji = payload.emoji.name
        event = self.events[msg_id]
        if emoji not in event["emoji_map"]:
            return  # Ce n’est pas un emoji de créneau valide

        # Ajouter l’utilisateur à la liste s’il n’y est pas déjà
        if payload.user_id not in event["participants"][emoji]:
            event["participants"][emoji].append(payload.user_id)

        # Refaire l'embed pour le mettre à jour
        channel = self.bot.get_channel(payload.channel_id)
        if channel is None:
            return
        try:
            message = await channel.fetch_message(msg_id)
        except discord.NotFound:
            return

        new_embed = self.build_embed(
            event["title"],
            event["date"],
            event["emoji_map"],
            event["participants"]
        )
        await message.edit(embed=new_embed)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """
        Déclenché quand quelqu'un retire une réaction.
        Si c’est un message d’event, on supprime l’utilisateur de ce créneau.
        """
        if payload.user_id == self.bot.user.id:
            return

        msg_id = payload.message_id
        if msg_id not in self.events:
            return

        emoji = payload.emoji.name
        event = self.events[msg_id]
        if emoji not in event["emoji_map"]:
            return

        # Enlever l’utilisateur du créneau s’il était dedans
        if payload.user_id in event["participants"][emoji]:
            event["participants"][emoji].remove(payload.user_id)

        # Refaire l’embed
        channel = self.bot.get_channel(payload.channel_id)
        if channel is None:
            return
        try:
            message = await channel.fetch_message(msg_id)
        except discord.NotFound:
            return

        new_embed = self.build_embed(
            event["title"],
            event["date"],
            event["emoji_map"],
            event["participants"]
        )
        await message.edit(embed=new_embed)


# <<< IMPORTANT pour discord.py 2.x (py-cord, nextcord, etc.) >>>
async def setup(bot):
    await bot.add_cog(EventCog(bot))
