import random
from datetime import datetime
from typing import Dict, Optional

import discord
from discord.ext import commands
from discord.ui import Button, View

from economy.stats import get_user_stats, load_stats, save_stats

SUITS = ["S", "H", "D", "C"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
MIN_BET = 50
MAX_BET = 10000


class Card:
    def __init__(self, suit: str, rank: str):
        self.suit = suit
        self.rank = rank

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

    def value(self) -> int:
        if self.rank in {"J", "Q", "K"}:
            return 10
        if self.rank == "A":
            return 11
        return int(self.rank)


class BlackjackGame:
    def __init__(self, player_id: int, bet: int):
        self.player_id = player_id
        self.bet = bet
        self.deck = [Card(suit, rank) for suit in SUITS for rank in RANKS] * 8
        random.shuffle(self.deck)
        self.player_hand = [self.deck.pop(), self.deck.pop()]
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]
        self.game_over = False
        self.result: Optional[str] = None
        self.payout = 0

    def calculate_hand_value(self, hand: list[Card]) -> int:
        value = sum(card.value() for card in hand)
        aces = sum(1 for card in hand if card.rank == "A")

        while value > 21 and aces > 0:
            value -= 10
            aces -= 1

        return value

    def hit_player(self) -> bool:
        self.player_hand.append(self.deck.pop())
        if self.calculate_hand_value(self.player_hand) > 21:
            self.game_over = True
            self.result = "bust"
            self.payout = 0
            return False
        return True

    def stand(self) -> None:
        while self.calculate_hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())

        player_value = self.calculate_hand_value(self.player_hand)
        dealer_value = self.calculate_hand_value(self.dealer_hand)

        if dealer_value > 21 or player_value > dealer_value:
            self.result = "win"
            self.payout = self.bet * 2
        elif dealer_value > player_value:
            self.result = "lose"
            self.payout = 0
        else:
            self.result = "push"
            self.payout = self.bet

        self.game_over = True

    def check_blackjack(self) -> bool:
        player_value = self.calculate_hand_value(self.player_hand)
        dealer_value = self.calculate_hand_value(self.dealer_hand)

        if len(self.player_hand) == 2 and player_value == 21:
            if len(self.dealer_hand) == 2 and dealer_value == 21:
                self.result = "push"
                self.payout = self.bet
            else:
                self.result = "blackjack"
                self.payout = int(self.bet * 2.5)
            self.game_over = True
            return True

        if len(self.dealer_hand) == 2 and dealer_value == 21:
            self.result = "lose"
            self.payout = 0
            self.game_over = True
            return True

        return False

    def render(self) -> str:
        player_value = self.calculate_hand_value(self.player_hand)
        player_cards = " ".join(str(card) for card in self.player_hand)

        if self.game_over:
            dealer_value = self.calculate_hand_value(self.dealer_hand)
            dealer_cards = " ".join(str(card) for card in self.dealer_hand)
            return (
                "```\n"
                "BLACKJACK\n\n"
                f"DEALER: {dealer_cards} ({dealer_value})\n"
                f"PLAYER: {player_cards} ({player_value})\n\n"
                f"Bet: {self.bet}\n"
                "```"
            )

        dealer_cards = f"{self.dealer_hand[0]} ?"
        return (
            "```\n"
            "BLACKJACK\n\n"
            f"DEALER: {dealer_cards}\n"
            f"PLAYER: {player_cards} ({player_value})\n\n"
            f"Bet: {self.bet}\n"
            "```"
        )


class BlackjackView(View):
    def __init__(self, cog: "BlackjackCog", game_id: str, player_id: int):
        super().__init__(timeout=120)
        self.cog = cog
        self.game_id = game_id
        self.player_id = player_id
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("🎰 This blackjack game is not yours.", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        game = self.cog.active_games.get(self.game_id)
        if not game:
            return
        game.stand()
        if self.message:
            try:
                await self.message.edit(
                    content=self.cog._build_result_message(game, "⏰ Time is up. Dealer plays automatically."),
                    view=None,
                )
            except discord.HTTPException:
                pass
        self.cog._finish_game(self.game_id, game)

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: Button) -> None:
        game = self.cog.active_games.get(self.game_id)
        if not game:
            return await interaction.response.send_message("🎰 This blackjack game is no longer active.", ephemeral=True)

        if not game.hit_player():
            await interaction.response.edit_message(
                content=self.cog._build_result_message(game, f"💥 Bust! You lost **{game.bet}** cheese."),
                view=None,
            )
            self.cog._finish_game(self.game_id, game)
            self.stop()
            return

        await interaction.response.edit_message(content=game.render(), view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.success)
    async def stand(self, interaction: discord.Interaction, button: Button) -> None:
        game = self.cog.active_games.get(self.game_id)
        if not game:
            return await interaction.response.send_message("🎰 This blackjack game is no longer active.", ephemeral=True)

        game.stand()
        await interaction.response.edit_message(
            content=self.cog._build_result_message(game),
            view=None,
        )
        self.cog._finish_game(self.game_id, game)
        self.stop()


class BlackjackCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games: Dict[str, BlackjackGame] = {}

    def _find_active_game_id(self, user_id: int) -> Optional[str]:
        for game_id, game in self.active_games.items():
            if game.player_id == user_id:
                return game_id
        return None

    def _finish_game(self, game_id: str, game: BlackjackGame) -> None:
        stats = load_stats()
        user = get_user_stats(stats, game.player_id)
        user["cheese"] += game.payout
        save_stats(stats)
        self.active_games.pop(game_id, None)

    def _build_result_message(self, game: BlackjackGame, prefix: str = "") -> str:
        result_text = {
            "win": "🎉 You win!",
            "lose": "💀 Dealer wins!",
            "push": "🤝 Push!",
            "blackjack": "⭐ Blackjack!",
            "bust": "💥 Bust!",
        }.get(game.result or "", "🎰 Round complete.")
        message = game.render()
        if prefix:
            message += f"\n{prefix}"
        else:
            message += f"\n{result_text}"
        message += f"\nPayout: **{game.payout}** cheese 🧀"
        return message

    @commands.command(name="blackjack", aliases=["bj"])
    async def blackjack(self, ctx: commands.Context, bet: int) -> None:
        stats = load_stats()
        user = get_user_stats(stats, ctx.author.id)

        if self._find_active_game_id(ctx.author.id):
            return await ctx.send("🎰 You already have an active blackjack game.")
        if bet < MIN_BET:
            return await ctx.send(f"🎲 Minimum bet is **{MIN_BET}** cheese.")
        if bet > MAX_BET:
            return await ctx.send(f"🚫 Maximum bet is **{MAX_BET}** cheese.")
        if user["cheese"] < bet:
            return await ctx.send("🫠 You do not have enough cheese.")

        user["cheese"] -= bet
        save_stats(stats)

        game_id = f"{ctx.author.id}_{int(datetime.utcnow().timestamp() * 1000)}"
        game = BlackjackGame(ctx.author.id, bet)
        self.active_games[game_id] = game

        if game.check_blackjack():
            if game.result == "blackjack":
                message = self._build_result_message(game, "⭐ Blackjack! You win instantly.")
            elif game.result == "push":
                message = self._build_result_message(game, "🤝 Both sides have blackjack.")
            else:
                message = self._build_result_message(game, "💀 Dealer has blackjack.")
            await ctx.send(message)
            self._finish_game(game_id, game)
            return

        view = BlackjackView(self, game_id, ctx.author.id)
        sent_message = await ctx.send(game.render(), view=view)
        view.message = sent_message

    @blackjack.error
    async def blackjack_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("🎰 Use `!blackjack <bet>` or `!bj <bet>`, for example `!blackjack 250`.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("🔢 Your bet must be a whole number.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BlackjackCog(bot))
