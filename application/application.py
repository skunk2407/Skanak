import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
from typing import Dict, Optional


class ApplyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Nouveau salon de dépôt des candidatures (mods)
        self.mod_channel_id = 1106197912075116614

        # Stocke le dernier message tapé par l'utilisateur (son "formulaire" brut)
        self.pending_applications: Dict[int, discord.Message] = {}

        # Map du message envoyé aux modos -> id du candidat
        self.review_index: Dict[int, int] = {}

        # Délai avant verdict auto (24h)
        self.review_delay_seconds = 24 * 60 * 60

    @commands.command()
    async def apply(self, ctx: commands.Context):
        """Command to start the application process."""
        button = Button(
            label="Start Application",
            style=discord.ButtonStyle.primary,
            custom_id="start_application"
        )
        view = View()
        view.add_item(button)
        await ctx.send("Click the button below to start your application:", view=view)

    # ===== Helpers =====

    def build_send_button(self, user_id: int) -> View:
        view = View()
        button = Button(
            label="Send",
            style=discord.ButtonStyle.success,
            custom_id=f"send_{user_id}"
        )
        view.add_item(button)
        return view

    async def _safe_dm(self, user: discord.abc.User, **send_kwargs) -> bool:
        """Essaye d'envoyer un DM. Retourne True si succès, False sinon."""
        try:
            await user.send(**send_kwargs)
            return True
        except discord.Forbidden:
            return False
        except discord.HTTPException:
            return False

    async def _schedule_review(self, channel_id: int, message_id: int, applicant_id: int):
        """Programme une vérification après le délai, puis notifie le candidat du verdict."""
        # Enregistre la relation pour pouvoir retrouver l'auteur après coup
        self.review_index[message_id] = applicant_id

        async def _worker():
            try:
                await asyncio.sleep(self.review_delay_seconds)

                # Récupère le message des modos
                channel = self.bot.get_channel(channel_id)
                if channel is None:
                    channel = await self.bot.fetch_channel(channel_id)

                mod_msg: Optional[discord.Message] = None
                try:
                    mod_msg = await channel.fetch_message(message_id)  # type: ignore
                except discord.NotFound:
                    mod_msg = None

                applicant: Optional[discord.User] = None
                try:
                    applicant = await self.bot.fetch_user(applicant_id)
                except Exception:
                    applicant = None

                if mod_msg is None or applicant is None:
                    return

                # Compte les votes ✅ / ❌ (on retire 1 si le bot a posé la réaction)
                approvals = 0
                rejects = 0
                bot_user = self.bot.user

                for reaction in mod_msg.reactions:
                    emoji = str(reaction.emoji)
                    if emoji not in ("✅", "❌"):
                        continue

                    count = reaction.count
                    subtract_bot_seed = 0
                    if bot_user is not None:
                        try:
                            async for u in reaction.users():
                                if u.id == bot_user.id:
                                    subtract_bot_seed = 1
                                    break
                        except Exception:
                            subtract_bot_seed = 1

                    votes = max(0, count - subtract_bot_seed)

                    if emoji == "✅":
                        approvals = votes
                    elif emoji == "❌":
                        rejects = votes

                # Détermine le verdict
                if approvals > rejects:
                    title = "✅ Application Approved"
                    color = discord.Color.green()
                    msg = "Good news! Your application has been **approved** by the moderators. Welcome aboard! 🎉"
                elif rejects > approvals:
                    title = "❌ Application Rejected"
                    color = discord.Color.red()
                    msg = "Sorry, your application has **not been approved** by the moderators. Thank you for applying."
                else:
                    title = "⏳ Application Pending"
                    color = discord.Color.blurple()
                    msg = "Your application did **not reach a clear majority** after 24 hours. A moderator will follow up soon."

                embed = discord.Embed(
                    title=title,
                    description=f"{msg}\n\n**Votes after 24h** — ✅ {approvals} · ❌ {rejects}",
                    color=color,
                )

                # Tente DM
                dm_ok = await self._safe_dm(applicant, embed=embed)
                if not dm_ok:
                    try:
                        await mod_msg.reply(
                            content=f"{applicant.mention if applicant else 'Applicant'}",
                            embed=embed,
                            mention_author=False,
                        )
                    except Exception:
                        pass
            finally:
                self.review_index.pop(message_id, None)

        asyncio.create_task(_worker())

    # ===== Listeners =====

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        self.pending_applications[message.author.id] = message

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id") if interaction.data else None
        if not custom_id:
            return

        if custom_id == "start_application":
            await interaction.response.send_message(
                content=(
                    "Please answer the following questions in **one single message**, "
                    "separated by commas (`,`), then click `Send` when you're done."
                ),
                embed=discord.Embed(
                    title="Application Questions",
                    description="\n".join(
                        [
                            "1. Why do you want to join?",
                            "2. Were you in any regiment? If yes, which one?",
                            "3. How many hours have you played? (in-game)",
                            "4. What's your in-game name?",
                            "5. Do you know anyone from our community?",
                            "6. What's your highest total kills in a single round?",
                        ]
                    ),
                    color=discord.Color.blue(),
                ),
                view=self.build_send_button(interaction.user.id),
                ephemeral=True,
            )
            return

        if custom_id.startswith("send_"):
            user_id = int(custom_id.split("_", maxsplit=1)[1])
            if interaction.user.id != user_id:
                await interaction.response.send_message(
                    "You can't send someone else's application.", ephemeral=True
                )
                return

            last_msg = self.pending_applications.get(user_id)
            if not last_msg:
                await interaction.response.send_message(
                    "No application message found. Please make sure you replied in the chat.",
                    ephemeral=True,
                )
                return

            responses = [resp.strip() for resp in last_msg.content.split(",") if resp.strip()]

            fields = [
                "1. Why do you want to join?",
                "2. Were you in any regiment? If yes, which one?",
                "3. How many hours have you played? (in-game)",
                "4. What's your in-game name?",
                "5. Do you know anyone from our community?",
                "6. What's your highest total kills in a single round?",
            ]

            final_msg = "\n".join(
                f"**{question}** {responses[i] if i < len(responses) else '❌ No answer ❌'}"
                for i, question in enumerate(fields)
            )

            mod_channel = self.bot.get_channel(self.mod_channel_id)
            if not isinstance(mod_channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)):
                try:
                    mod_channel = await self.bot.fetch_channel(self.mod_channel_id)
                except Exception:
                    mod_channel = None

            if mod_channel is None:
                await interaction.response.send_message("Mod channel not found.", ephemeral=True)
                return

            embed = discord.Embed(
                title="📩 New Application",
                description=final_msg,
                color=discord.Color.green(),
            )
            embed.set_author(name=str(last_msg.author), icon_url=last_msg.author.display_avatar.url)

            mod_msg = await mod_channel.send(
                content=f"New application from {last_msg.author.mention}:", embed=embed
            )
            try:
                await mod_msg.add_reaction("✅")
                await mod_msg.add_reaction("❌")
            except discord.HTTPException:
                pass

            try:
                await last_msg.delete()
            except (discord.Forbidden, discord.HTTPException):
                pass

            await interaction.response.send_message(
                "✅ Your application has been sent to the moderators!", ephemeral=True
            )

            await self._schedule_review(mod_msg.channel.id, mod_msg.id, last_msg.author.id)
            self.pending_applications.pop(user_id, None)


async def setup(bot: commands.Bot):
    await bot.add_cog(ApplyCog(bot))
