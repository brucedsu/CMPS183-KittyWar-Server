import random

from logger import Logger, LogCodes
from network import Flags
from threading import Lock
from enum import IntEnum
from cat import Moves, Cats
from ability import Ability
from chance import Chance


class Phases(IntEnum):

    SETUP = 0
    PRELUDE = 1
    ENACT_STRATS = 2
    SHOW_CARDS = 3
    SETTLE_STRATS = 4
    POSTLUDE = 5


class Player:

    def __init__(self, username, cats, network, socket):

        self.username = username
        self.cats = cats
        self.socket = socket
        self.network = network

        self.__cat = None
        self.rability = 0
        self.health = 0
        self.healed = 0

        self.base_damage = 1
        self.dmg_dealt = 0
        self.dmg_taken = 0
        self.dmg_dodged = 0
        self.modifier = 1
        self.pierce = False
        self.reverse = False
        self.irreversible = False
        self.invulnerable = False
        self.spotlight = False

        self.chance_cards = []
        self.used_cards = []
        self.cooldowns = []

        self.move = None
        self.selected_chance = False
        self.ready = False

        self.winner = False

    @property
    def cat(self):
        return self.__cat

    @cat.setter
    def cat(self, cat):

        self.__cat = cat
        self.health = cat.hp

    # Grab the players chance card at a certain index
    # index 1 = most recently added card
    # index 2 = second most recently added card... etc.
    @property
    def chance_card(self, index=1):

        last_index = len(self.chance_cards) - index

        if last_index >= 0:
            return self.chance_cards[last_index]

        return None

    @property
    def used_card(self):

        last_index = len(self.used_cards) - 1

        if last_index >= 0:
            return self.used_cards[last_index]

        return None


class Match:

    def __init__(self):

        self.lock = Lock()
        self.match_valid = True
        self.result = None
        self.winner = None

        self.phase = Phases.SETUP
        self.p1 = None
        self.p2 = None

    def process_request(self, username, request):

        if self.match_valid:

            player = self.get_player(username)
            phase_map[self.phase](self, player, request)

        return self.match_valid

    # Ends the match in an error
    def kill_match(self):

        self.match_valid = False
        self.result = Flags.ERROR
        self.alert_players(Flags.END_MATCH, Flags.ONE_BYTE, Flags.ERROR)

    def disconnect(self, username):

        Logger.log(username + " has disconnected from their match", LogCodes.Match)
        Logger.log(username + " will be assessed with a loss", LogCodes.Match)

        self.match_valid = False

        opponent = self.get_opponent(username)

        # The disconnected player gets a loss - notify the winning player
        response = opponent.network.generate_responseb(Flags.END_MATCH, Flags.ONE_BYTE, Flags.SUCCESS)
        opponent.network.send_data(opponent.username, opponent.socket, response)

    # A win condition has been met stopping the match
    def end_match(self):

        Logger.log("Match ending for " + self.p1.username + " & " +
                   self.p2.username, LogCodes.Match)

        self.match_valid = False

        self.result = Flags.SUCCESS
        if self.p1.winner and self.p2.winner:

            Logger.log("The match is a draw", LogCodes.Match)
            self.result = Flags.DRAW
            self.alert_players(Flags.END_MATCH, Flags.ONE_BYTE, Flags.DRAW)
            return

        elif self.p1.winner:

            self.winner = self.p1
            p1_response = self.p1.network.generate_responseb(Flags.END_MATCH, Flags.ONE_BYTE, Flags.SUCCESS)
            p2_response = self.p2.network.generate_responseb(Flags.END_MATCH, Flags.ONE_BYTE, Flags.FAILURE)

        else:

            self.winner = self.p2
            p2_response = self.p2.network.generate_responseb(Flags.END_MATCH, Flags.ONE_BYTE, Flags.SUCCESS)
            p1_response = self.p1.network.generate_responseb(Flags.END_MATCH, Flags.ONE_BYTE, Flags.FAILURE)

        Logger.log(self.winner.username + " has won the match", LogCodes.Match)
        self.p1.network.send_data(self.p1.username, self.p1.socket, p1_response)
        self.p2.network.send_data(self.p2.username, self.p2.socket, p2_response)

    # Phase before prelude for handling match preparation
    def setup(self, player, request):

        flag = request.flag
        if flag == Flags.SELECT_CAT:
            self.select_cat(player, request)

        elif flag == Flags.READY:

            # Set the player to ready and assign random ability and two random chance cards
            players_ready = self.player_ready(player)

            Ability.random_ability(player)
            Chance.random_chance(player)
            Chance.random_chance(player)

            # If both players are ready proceed to the next phase
            if players_ready:

                # Set and alert players of next phase
                self.next_phase(Phases.PRELUDE)

                # Do not proceed if someone did not select a cat but readied up
                if self.p1.cat is not None and \
                        self.p2.cat is not None:

                    self.post_setup()
                    self.gloria_prelude()

                else:

                    Logger.log("One of the players did not select a cat - Killing the match", LogCodes.Match)
                    self.kill_match()

    # Notifies players about cats abilities and chances before game moves on
    def post_setup(self):

        Logger.log("Post setup running for " + self.p1.username +
                   ", " + self.p2.username, LogCodes.Match)

        # Send player1 player2's cat & send player2 player1's cat
        p1_response = self.p1.network.generate_responseb(Flags.OP_CAT, Flags.ONE_BYTE, self.p2.cat.id)
        p2_response = self.p2.network.generate_responseb(Flags.OP_CAT, Flags.ONE_BYTE, self.p1.cat.id)

        # Send player1 their random ability & send player 2 their random ability
        p1_response += self.p1.network.generate_responseb(Flags.GAIN_ABILITY, Flags.ONE_BYTE, self.p1.rability)
        p2_response += self.p2.network.generate_responseb(Flags.GAIN_ABILITY, Flags.ONE_BYTE, self.p2.rability)

        # Send player1 their two random chance cards
        p1_response += self.p1.network.generate_responseh(Flags.GAIN_CHANCES, Flags.TWO_BYTE)
        p1_response.append(self.p1.chance_cards[0])
        p1_response.append(self.p1.chance_cards[1])

        # Send player2 their two random chance cards
        p2_response += self.p2.network.generate_responseh(Flags.GAIN_CHANCES, Flags.TWO_BYTE)
        p2_response.append(self.p2.chance_cards[0])
        p2_response.append(self.p2.chance_cards[1])

        self.p1.network.send_data(self.p1.username, self.p1.socket, p1_response)
        self.p2.network.send_data(self.p2.username, self.p2.socket, p2_response)

    # Activates any prelude passive abilities the players have
    def gloria_prelude(self):

        Logger.log("Prelude phase starting for " + self.p1.username +
                   ", " + self.p2.username, LogCodes.Match)

        # Reset players per round stats
        self.reset_attributes(self.p1)
        self.reset_attributes(self.p2)

        # Decrease any abilities on cooldown
        Ability.decrease_cooldowns(self.p1)
        Ability.decrease_cooldowns(self.p2)

        # Check passive abilities
        Ability.use_passive_ability(self.p1, self.p2, self.phase)
        Ability.use_passive_ability(self.p1, self.p2, self.phase, self.p1.rability)

        Ability.use_passive_ability(self.p2, self.p1, self.phase)
        Ability.use_passive_ability(self.p2, self.p1, self.phase, self.p2.rability)

    def prelude(self, player, request):

        flag = request.flag
        if flag == Flags.USE_ABILITY:
            self.select_ability(player, request)

        elif flag == Flags.READY:

            players_ready = self.player_ready(player)
            if players_ready:

                # Set and alert players of next phase
                self.next_phase(Phases.ENACT_STRATS)
                self.gloria_enact_strats()

    # Log the enact strats phase starting
    def gloria_enact_strats(self):

        Logger.log("Enact Strategies phase starting for " + self.p1.username +
                   ", " + self.p2.username, LogCodes.Match)

    def enact_strats(self, player, request):

        flag = request.flag
        if flag == Flags.SELECT_MOVE:
            self.select_move(player, request)

        elif flag == Flags.USE_CHANCE:
            self.select_chance(player, request)

        elif flag == Flags.READY:

            players_ready = self.player_ready(player)
            if players_ready:

                # Notify player of next round
                self.next_phase(Phases.SHOW_CARDS)

                # Before moving on check both players selected a move
                if self.p1.move is not None and \
                        self.p2.move is not None:

                    self.gloria_show_cards()

                else:

                    Logger.log("One of the players did not select a move - Killing match", LogCodes.Match)
                    self.kill_match()

    def gloria_show_cards(self):

        Logger.log("Show Cards phase starting for " + self.p1.username +
                   ", " + self.p2.username, LogCodes.Match)

        # Show player1 player2's move
        p1_response = self.p1.network.generate_responseb(Flags.REVEAL_MOVE, Flags.ONE_BYTE, self.p2.move)

        # Show player2 player1's move
        p2_response = self.p2.network.generate_responseb(Flags.REVEAL_MOVE, Flags.ONE_BYTE, self.p1.move)

        # Show player1 player2's chance card if they selected one
        if self.p2.selected_chance:
            p1_response += self.p1.network.generate_responseb(
                Flags.REVEAL_CHANCE, Flags.ONE_BYTE, self.p2.used_card)
        else:
            p1_response += self.p1.network.generate_responseh(Flags.REVEAL_CHANCE, Flags.ZERO_BYTE)

        # Show player2 player1's chance card if they selected one
        if self.p1.selected_chance:
            p2_response += self.p2.network.generate_responseb(
                Flags.REVEAL_CHANCE, Flags.ONE_BYTE, self.p1.used_card)
        else:
            p2_response += self.p2.network.generate_responseh(Flags.REVEAL_CHANCE, Flags.ZERO_BYTE)

        self.p1.network.send_data(self.p1.username, self.p1.socket, p1_response)
        self.p2.network.send_data(self.p2.username, self.p2.socket, p2_response)

    def show_cards(self, player, request):

        flag = request.flag
        if flag == Flags.READY:

            players_ready = self.player_ready(player)
            if players_ready:

                self.next_phase(Phases.SETTLE_STRATS)
                self.gloria_settle_strats()

    def gloria_settle_strats(self):

        Logger.log("Settle Strategies phase starting for " + self.p1.username +
                   ", " + self.p2.username, LogCodes.Match)

        # Use player1's chance card if pre settle
        if self.p1.selected_chance and Chance.pre_settle(self.p1.used_card):
            Chance.use_chance(self.p1.used_card, self.p1)

        # Use player2's chance card if pre settle
        if self.p2.selected_chance and Chance.pre_settle(self.p2.used_card):
            Chance.use_chance(self.p2.used_card, self.p2)

        # Determine combat order
        # Player1 goes first if they have spotlight and player2 does not
        if self.p1.spotlight and not self.p2.spotlight:

            player = self.p1
            opponent = self.p2

        # Player2 goes first if they have spotlight and player2 does not
        elif self.p2.spotlight and not self.p1.spotlight:

            player = self.p2
            opponent = self.p1

        # Randomly choose order if neither or both players have spotlight
        else:

            player = self.get_random_player()
            opponent = self.get_opponent(player.username)

        # var player is the designated variable for who does first
        self.handle_combat(player, opponent)
        self.handle_combat(opponent, player)

        # Use player1's chance card if post settle
        if self.p1.selected_chance and Chance.post_settle(self.p1.used_card):

            chance_used = Chance.use_chance(self.p1.used_card, self.p1)
            if chance_used:
                Chance.chance_responses(self.p1.used_card, self.p1, self.p2)

        # Use player2's chance card if post settle
        if self.p2.selected_chance and Chance.post_settle(self.p2.used_card):

            chance_used = Chance.use_chance(self.p2.used_card, self.p2)
            if chance_used:
                Chance.chance_responses(self.p2.used_card, self.p2, self.p1)

        # Send new HPs to clients
        # Send player1 their damage taken and notify opponent as well
        damage_taken = self.p1.health
        p1_response = self.p1.network.generate_responseb(
            Flags.GAIN_HP, Flags.ONE_BYTE, damage_taken)

        p2_response = self.p2.network.generate_responseb(
            Flags.OP_GAIN_HP, Flags.ONE_BYTE, damage_taken)

        # Send player2 their damage taken and notify opponent as well
        damage_taken = self.p2.health
        p2_response += self.p2.network.generate_responseb(
            Flags.GAIN_HP, Flags.ONE_BYTE, damage_taken)

        p1_response += self.p1.network.generate_responseb(
            Flags.OP_GAIN_HP, Flags.ONE_BYTE, damage_taken)

        # Send all chance cards each player has
        # Send for player1
        p1_response += self.p1.network.generate_responseh(Flags.GAIN_CHANCES, len(self.p1.chance_cards))
        for chance_card in self.p1.chance_cards:
            p1_response.append(chance_card)

        # Send for player2
        p2_response += self.p2.network.generate_responseh(Flags.GAIN_CHANCES, len(self.p2.chance_cards))
        for chance_card in self.p2.chance_cards:
            p2_response.append(chance_card)

        self.p1.network.send_data(self.p1.username, self.p1.socket, p1_response)
        self.p2.network.send_data(self.p2.username, self.p2.socket, p2_response)

        self.check_winner()

    def settle_strats(self, player, request):

        flag = request.flag
        if flag == Flags.READY:

            players_ready = self.player_ready(player)
            if players_ready:
                self.next_phase(Phases.POSTLUDE)
                self.gloria_postlude()

    def gloria_postlude(self):

        Logger.log("Postlude phase starting for " + self.p1.username +
                   ", " + self.p2.username, LogCodes.Match)

        Ability.use_passive_ability(self.p1, self.p2, self.phase)
        Ability.use_passive_ability(self.p1, self.p2, self.phase, self.p1.rability)

        Ability.use_passive_ability(self.p2, self.p1, self.phase)
        Ability.use_passive_ability(self.p2, self.p1, self.phase, self.p2.rability)

    def postlude(self, player, request):

        flag = request.flag
        if flag == Flags.USE_ABILITY:
            self.select_ability(player, request)

        elif flag == Flags.READY:

            players_ready = self.player_ready(player)
            if players_ready:

                self.check_winner()
                self.next_phase(Phases.PRELUDE)
                self.gloria_prelude()

    # Returns player one or two based on username
    def get_player(self, username):

        if self.p1.username == username:
            return self.p1
        else:
            return self.p2

    # Returns one of the two players randomly
    def get_random_player(self):

        randnum = random.randrange(0, 2)
        if randnum == 0:
            return self.p1
        else:
            return self.p2

    # Returns the player that does not have the specified username
    def get_opponent(self, username):

        if self.p1.username == username:
            return self.p2
        else:
            return self.p1

    # Sends a message to both players with or without a body
    def alert_players(self, flag, size=None, body=None):

        # Check if there is a body to send
        if size is None:

            p1_response = self.p1.network.generate_responseh(flag, Flags.ZERO_BYTE)
            p2_response = self.p2.network.generate_responseh(flag, Flags.ZERO_BYTE)

        else:

            p1_response = self.p1.network.generate_responseb(flag, size, body)
            p2_response = self.p2.network.generate_responseb(flag, size, body)

        self.p1.network.send_data(self.p1.username, self.p1.socket, p1_response)
        self.p2.network.send_data(self.p2.username, self.p2.socket, p2_response)

    # Move onto the next phase specified and alert the players
    def next_phase(self, phase):

        self.reset_ready()
        self.phase = phase
        self.alert_players(Flags.NEXT_PHASE)

    # Set a player to ready and return whether both are ready or not
    def player_ready(self, player):

        player.ready = True
        return self.p1.ready and self.p2.ready

    # Sets both players to not ready
    def reset_ready(self):

        self.p1.ready = False
        self.p2.ready = False

    # Handles the user attempting to select a cat
    @staticmethod
    def select_cat(player, request):

        cat_id = -1
        if request.body:
            cat_id = int(request.body)

        cat_selected = Cats.select_cat(player, cat_id)

        if cat_selected:
            Logger.log(player.username + " has selected their cat" +
                       " - id: " + str(cat_id), LogCodes.Match)

        else:
            Logger.log(player.username + " could not select their cat" +
                       " - id: " + str(cat_id), LogCodes.Match)

        response = player.network.generate_responseb(Flags.SELECT_CAT, Flags.ONE_BYTE, int(cat_selected))
        player.network.send_data(player.username, player.socket, response)

    # Handles the user attempting to select a move
    @staticmethod
    def select_move(player, request):

        move = -1
        if request.body:
            move = int(request.body)

        move_selected = Moves.select_move(player, move)

        if move_selected:
            Logger.log(player.username + " has selected their move" +
                       " - id: " + str(move), LogCodes.Match)

        else:
            Logger.log(player.username + " could not select their move" +
                       " - id: " + str(move), LogCodes.Match)

        response = player.network.generate_responseb(Flags.SELECT_MOVE, Flags.ONE_BYTE, int(move_selected))
        player.network.send_data(player.username, player.socket, response)

    # Handles the user attempting to select a chance card
    @staticmethod
    def select_chance(player, request):

        chance = -1
        if request.body:
            chance = int(request.body)

        chance_selected = Chance.select_chance(player, chance)

        if chance_selected:
            Logger.log(player.username + " has selected their chance" +
                       " - id: " + str(chance), LogCodes.Match)

        else:
            Logger.log(player.username + " could not select their chance" +
                       " - id: " + str(chance), LogCodes.Match)

        response = player.network.generate_responseb(Flags.USE_CHANCE, Flags.ONE_BYTE, int(chance_selected))
        player.network.send_data(player.username, player.socket, response)

    # Handles the user attempting to use an active ability
    def select_ability(self, player, request):

        ability_id = -1
        if request.body:
            ability_id = int(request.body)

        opponent = self.get_opponent(player.username)
        ability_used = Ability.use_active_ability(player, opponent, self.phase, ability_id)

        response = player.network.generate_responseb(Flags.USE_ABILITY, Flags.ONE_BYTE, int(ability_used))
        player.network.send_data(player.username, player.socket, response)

    # Determine if a win condition has been met
    def check_winner(self):

        winner = False
        if self.p1.health == 20 or \
                self.p2.health == 0:

            self.p1.winner = True
            winner = True

        if self.p2.health == 20 or \
                self.p1.health == 0:

            self.p2.winner = True
            winner = True

        if winner:
            self.end_match()

    # Reset per round game stats for a player
    @staticmethod
    def reset_attributes(player):

        player.healed = 0
        player.dmg_dealt = 0
        player.dmg_taken = 0
        player.dmg_dodged = 0
        player.modifier = 1
        player.pierce = False
        player.reverse = False
        player.irreversible = False
        player.invulnerable = False
        player.spotlight = False

        player.move = None
        player.selected_chance = False

    @staticmethod
    def handle_combat(player, opponent):

        # Handle combat scenarios for players

        # If the player scratches
        if player.move == Moves.SCRATCH:

            damage = player.base_damage * player.modifier

            # opponent guards
            if opponent.move == Moves.GUARD:

                # Player does not have pierce
                if opponent.reverse and player.irreversible \
                        or not player.pierce:

                    opponent.dmg_dodged += damage

                # Damage is reversed
                elif opponent.reverse:

                    player.health -= damage
                    player.dmg_dealt += damage
                    player.dmg_taken += damage

                # Damage goes through
                elif player.pierce:

                    opponent.health -= damage
                    opponent.dmg_taken += damage
                    player.dmg_dealt += damage

            # opponent purrs scenarios
            elif opponent.move == Moves.PURR:

                # Opponent is not invulnerable otherwise nothing happens
                if not opponent.invulnerable:

                    opponent.health -= 1
                    opponent.dmg_taken += 1
                    player.dmg_dealt += 1

            # If the opponent is scratching or skipping
            else:

                opponent.health -= damage
                opponent.dmg_taken += damage
                player.dmg_dealt += damage

        # If the player purrs and is invulnerable while the opponent is scratching
        elif player.move == Moves.PURR and opponent.move == Moves.SCRATCH:

            if player.invulnerable:

                player.health += 1
                player.healed += 1

        # If the player purrs while the opponent does not scratch
        elif player.move == Moves.PURR and not opponent.move == Moves.SCRATCH:

            player.health += 1
            player.healed += 1

phase_map = {

    Phases.SETUP: Match.setup,
    Phases.PRELUDE: Match.prelude,
    Phases.ENACT_STRATS: Match.enact_strats,
    Phases.SHOW_CARDS: Match.show_cards,
    Phases.SETTLE_STRATS: Match.settle_strats,
    Phases.POSTLUDE: Match.postlude
}
