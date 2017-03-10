import random

from logger import Logger, LogCodes
from network import Network, Flags
from enum import IntEnum
from cat import Moves


class Chances(IntEnum):

    @staticmethod
    def valid_chance(chance):
        return chance in list(map(int, Chances))

    DOUBLE_PURR = 0
    GUARANTEED_PURR = 1
    PURR_DRAW = 2
    REVERSE_SCRATCH = 3
    GUARD_HEAL = 4
    GUARD_DRAW = 5
    NO_REVERSE = 6
    NO_GUARD = 7
    DOUBLE_SCRATCH = 8


class Chance:

    @staticmethod
    def valid_chance(chance):
        return Chances.valid_chance(chance)

    # Assigns a random chance card to the specified player
    @staticmethod
    def random_chance(player):

        chance_card = random.randrange(0, 9)
        player.chance_cards.append(chance_card)

    # Checks if the player has the chance card they selected to use
    @staticmethod
    def has_chance(player, chance):

        has = player.chance_cards.count(chance) != 0

        if has:
            Logger.log(player.username + " has chance card: " + str(chance), LogCodes.Chance)
        else:
            Logger.log(player.username + " does not have chance card: " + str(chance), LogCodes.Chance)

        Logger.log(player.username + "'s currently owned chance cards: " + str(player.chance_cards), LogCodes.Chance)

        return has

    # Handles the user selecting a chance to use
    @staticmethod
    def select_chance(player, chance):

        valid_chance = Chance.valid_chance(chance)
        matches_move = Chance.matches_move(player, chance)
        has_chance = Chance.has_chance(player, chance)
        selected_chance = player.selected_chance
        skipping = player.move == Moves.SKIP

        valid = valid_chance and matches_move and has_chance \
            and not selected_chance and not skipping

        if valid:

            player.used_cards.append(chance)
            player.chance_cards.remove(chance)
            player.selected_chance = True

        return valid

    # Handles the user using a chance they selected
    @staticmethod
    def use_chance(chance_card, player):
        chance_map[chance_card](player)

    # Check if the chance corresponds with the selected move
    @staticmethod
    def matches_move(player, chance):

        matches = False
        if player.move is not None:

            if chance <= Chances.PURR_DRAW:
                matches = player.move == Moves.PURR

            elif chance <= Chances.GUARD_DRAW:
                matches = player.move == Moves.GUARD

            else:
                matches = player.move == Moves.SCRATCH

        Logger.log(player.username + "'s selected move: " + str(player.move), LogCodes.Chance)
        Logger.log(player.username + "'s chance they want to use: " + str(chance), LogCodes.Chance)
        Logger.log(player.username + " chance matches move: " + str(matches), LogCodes.Chance)
        return matches

    # Check if a particular chance should be used before settling the strategies
    @staticmethod
    def pre_settle(chance):

        return chance == Chances.REVERSE_SCRATCH or \
               chance == Chances.NO_REVERSE or \
               chance == Chances.NO_GUARD or \
               chance == Chances.DOUBLE_SCRATCH or \
               chance == Chances.GUARANTEED_PURR

    # Check if a particular chance should be used after settling the strategies
    @staticmethod
    def post_settle(chance):

        return chance == Chances.DOUBLE_PURR or \
               chance == Chances.PURR_DRAW or \
               chance == Chances.GUARD_HEAL or \
               chance == Chances.GUARD_DRAW

    # Chance 00 - Double Purring
    # Gain 2 HP if you don't get attacked
    @staticmethod
    def chance_00(player):

        chance_used = False
        if player.dmg_taken == 0:

            player.health += 2
            player.healed += 2
            Logger.log(player.username + " using Purr Chance 00 Double Purring", LogCodes.Chance)
            Logger.log(player.username + " gained two health points for not taking damage", LogCodes.Chance)
            chance_used = True

        else:
            Logger.log(player.username + " could not use Purr Chance 00 Double Purring", LogCodes.Chance)

        return chance_used

    # Chance 01 - Guaranteed Purring
    # Gain 1 HP no matter what
    @staticmethod
    def chance_01(player):

        player.health += 1
        player.healed += 1
        player.invulnerable = True
        Logger.log(player.username + " using Purr Chance 01 Guaranteed Purring", LogCodes.Chance)
        Logger.log(player.username + " gained one health point and is now invulnerable", LogCodes.Chance)

    # Chance 02 - Purr and Draw
    # Gain 1 chance card if you heal
    @staticmethod
    def chance_02(player):

        chance_used = False
        if player.healed > 0:

            Chance.random_chance(player)
            Logger.log(player.username + " using Purr Chance 02 Purr and Draw", LogCodes.Chance)
            Logger.log(player.username + " gained one chance card for healing", LogCodes.Chance)
            chance_used = True

        else:
            Logger.log(player.username + " could not use Purr Chance 02 Purr and Draw", LogCodes.Chance)

        return chance_used

    # Chance 03 - Reverse Scratch
    # Reverse the damage
    @staticmethod
    def chance_03(player):

        player.reverse = True
        Logger.log(player.username + " using Guard Chance 03 Reverse Scratch", LogCodes.Chance)
        Logger.log(player.username + "'is reversing incoming damage", LogCodes.Chance)

    # Chance 04 - Guard and Heal
    # Gain 1 HP if you dodge
    @staticmethod
    def chance_04(player):

        chance_used = False
        if player.dmg_dodged > 0:

            player.health += 1
            player.healed += 1
            Logger.log(player.username + " using Guard Chance 04 Guard and Heal", LogCodes.Chance)
            Logger.log(player.username + " gained one health point for dodging", LogCodes.Chance)
            chance_used = True

        else:
            Logger.log(player.username + " could not use Guard Chance 04 Guard and Heal", LogCodes.Chance)

        return chance_used

    # Chance 05 - Guard and Draw
    # Gain 1 chance card if you dodge
    @staticmethod
    def chance_05(player):

        chance_used = False
        if player.dmg_dodged > 0:

            Chance.random_chance(player)
            Logger.log(player.username + " using Guard Chance 05 Guard and Draw", LogCodes.Chance)
            Logger.log(player.username + " gained one chance card for dodging", LogCodes.Chance)
            chance_used = True

        else:
            Logger.log(player.username + " could not use Guard Chance 05 Guard and Draw", LogCodes.Chance)

        return chance_used

    # Chance 06 - Cant't reverse
    # Can't reverse the damage
    @staticmethod
    def chance_06(player):

        player.irreversible = True
        Logger.log(player.username + " using Scratch Chance 06 Can't Reverse", LogCodes.Chance)
        Logger.log(player.username + "'s attack can't be reversed", LogCodes.Chance)

    # Chance 07 - Can't Guard
    # Scratch can't be dodged
    @staticmethod
    def chance_07(player):

        player.pierce = True
        Logger.log(player.username + " using Scratch Chance 07 Can't Guard", LogCodes.Chance)
        Logger.log(player.username + "'s attack can't be dodged", LogCodes.Chance)

    # Chance 08 - Double Scratch
    # Scratch twice - x2 Damage
    @staticmethod
    def chance_08(player):

        player.modifier *= 2
        Logger.log(player.username + " using Scratch Chance 08 Double Scratch", LogCodes.Chance)
        Logger.log(player.username + "'s Attack Modifier: " + str(player.modifier), LogCodes.Chance)

    @staticmethod
    def chance_responses(chance_id, player, opponent):

        if chance_id == Chances.GUARD_DRAW or \
                chance_id == Chances.PURR_DRAW:

            response = Network.generate_responseb(Flags.GAIN_CHANCE, Flags.ONE_BYTE, player.chance_card)
            Network.send_data(player.username, player.connection, response)

            response = Network.generate_responseh(Flags.OP_GAIN_CHANCE, Flags.ZERO_BYTE)
            Network.send_data(opponent.username, opponent.connection, response)

chance_map = {

    Chances.DOUBLE_PURR: Chance.chance_00,
    Chances.GUARANTEED_PURR: Chance.chance_01,
    Chances.PURR_DRAW: Chance.chance_02,
    Chances.REVERSE_SCRATCH: Chance.chance_03,
    Chances.GUARD_HEAL: Chance.chance_04,
    Chances.GUARD_DRAW: Chance.chance_05,
    Chances.NO_REVERSE: Chance.chance_06,
    Chances.NO_GUARD: Chance.chance_07,
    Chances.DOUBLE_SCRATCH: Chance.chance_08
}
