import random
import match

from logger import Logger, LogCodes
from network import Network, Flags
from enum import IntEnum
from chance import Chance, Chances
from cat import Moves


class Abilities(IntEnum):

    Rejuvenation = 0
    Gentleman = 1
    Hunting = 2
    Recycling = 3
    Loneliness = 4
    Spotlight = 5
    Attacker = 6
    Critical = 7


class Ability:

    # Returns true if the ability is an active ability
    @staticmethod
    def is_active(ability_id):
        return ability_id in active_map

    # Returns true if the ability is a passive ability
    @staticmethod
    def is_passive(ability_id):
        return ability_id in passive_map

    # Checks if an ability is on cooldown
    @staticmethod
    def on_cooldown(player, ability_id):

        cd = False
        for cooldown in player.cooldowns:

            if cooldown[0] == ability_id:
                cd = True
                break

        return cd

    # Gives a random ability to the given player
    @staticmethod
    def random_ability(player):

        ability_id = random.randrange(6, 8)
        player.rability = ability_id

        Logger.log(player.username + " received random ability: " + str(ability_id), LogCodes.Ability)

    @staticmethod
    def use_active_ability(player, opponent, phase, ability_id):

        ability_used = False

        # Verify the ability can be used
        # Either the cat has the ability or it is a random ability
        useable = ability_id == player.cat.ability_id or ability_id == player.rability

        # The ability passed the previous inspection and it is no on cooldown
        useable = useable and not Ability.on_cooldown(player, ability_id)

        if useable and Ability.is_active(ability_id):

            Logger.log(player.username +
                       " attempting to use active ability - id: " + str(ability_id), LogCodes.Ability)

            ability_used = active_map[ability_id](phase, player)
            if ability_used:
                Ability.network_responses(ability_id, player, opponent)

        return ability_used

    @staticmethod
    def use_passive_ability(player, opponent, phase, ability_id=None):

        if ability_id is None:
            ability_id = player.cat.ability_id

        useable = not Ability.on_cooldown(player, ability_id)
        if useable and Ability.is_passive(ability_id):

            Logger.log(player.username +
                       " using passive ability - id: " + str(ability_id), LogCodes.Ability)

            ability_used = passive_map[ability_id](phase, player)
            if ability_used:
                Ability.network_responses(player, opponent, ability_id)

    # Decreases all the abilities on cooldown for a player by one
    @staticmethod
    def decrease_cooldowns(player):

        cooldowns = []
        for cooldown in player.cooldowns:

            time_remaining = cooldown[1] - 1
            if time_remaining == 0:
                continue

            new_cooldown = (cooldown[0], time_remaining)
            cooldowns.append(new_cooldown)

        player.cooldowns = cooldowns
        Logger.log(player.username + "'s current cooldowns: " + str(cooldowns), LogCodes.Ability)

    # Active Abilities
    # ##################################################################################################################

    # Ability 00 - Rejuvenation
    # Gain 1 HP - POSTLUDE - Cooldown: 2
    @staticmethod
    def a_ability00(phase, player):

        ability_used = False
        if phase == match.Phases.POSTLUDE:

            player.health += 1
            player.healed += 1
            player.cooldowns.append((Abilities.Rejuvenation, 3))

            ability_used = True
            Logger.log(player.username + " used Rejuvenation +1 Health Point", LogCodes.Ability)

        return ability_used

    # Ability 03 - Recycling
    # Random draw a chance card for used cards - POSTLUDE - Cooldown: 2
    @staticmethod
    def a_ability03(phase, player):

        ability_used = False
        used_count = len(player.used_cards)

        if phase == match.Phases.POSTLUDE:
            if used_count:

                random_card = random.randrange(0, used_count)
                player.chance_cards.append(random_card)
                player.used_cards.remove(random_card)

                ability_used = True
                Logger.log(player.username + "used recycling +1 used Chance Card", LogCodes.Ability)

        return ability_used

    # Ability 04 - Loneliness
    # Skip turn and gain 2 chance cards - PRELUDE - Cooldown: 2
    @staticmethod
    def a_ability04(phase, player):

        ability_used = False
        if phase == match.Phases.PRELUDE:

            Moves.select_move(player, Moves.SKIP)
            Logger.log(player.username + " has selected their move" +
                       " - id: " + str(Moves.SKIP), LogCodes.Ability)

            Chance.random_chance(player)
            Chance.random_chance(player)
            player.cooldowns.append((Abilities.Loneliness, 3))

            ability_used = True
            Logger.log(player.username + " used loneliness Skipping turn & +2 Chance Cards", LogCodes.Ability)

        return ability_used

    # Ability 05 - Spotlight
    # First in strategy settlement - PRELUDE - Cooldown: 2
    @staticmethod
    def a_ability05(phase, player):

        ability_used = False
        if phase == match.Phases.PRELUDE:

            player.spotlight = True
            player.cooldowns.append((Abilities.Spotlight, 3))

            ability_used = True
            Logger.log(player.username + " used Spotlight", LogCodes.Ability)

        return ability_used

    # Ability 07 - Critical Hit
    # Modifier x2 - PRELUDE - Cooldown: 2
    @staticmethod
    def a_ability07(phase, player):

        ability_used = False
        if phase == match.Phases.PRELUDE:

            player.modifier *= 2
            player.cooldowns.append((Abilities.Critical, 3))

            ability_used = True
            Logger.log(player.username + " used Critical Hit 2x Damage", LogCodes.Ability)

        return ability_used

    # Passive Abilities
    # ##################################################################################################################

    # Ability 01 - Gentleman
    # chance gained on condition - POSTLUDE
    # condition: damage dodged >= 2
    @staticmethod
    def p_ability01(phase, player):

        ability_used = False
        if phase == match.Phases.POSTLUDE:
            if player.dmg_dodged >= 2:

                Chance.random_chance(player)

                ability_used = True
                Logger.log(player.username + " used Gentleman +1 Chance Card", LogCodes.Ability)

        return ability_used

    # Ability 02 - Hunting
    # give player a "can't guard" or "can't reverse" card - POSTLUDE - Cooldown: 2
    # condition: does not have either cards in hand
    @staticmethod
    def p_ability02(phase, player):

        ability_used = False
        if phase == match.Phases.POSTLUDE:

            if not Chance.has_chance(player, Chances.NO_GUARD) and\
                    not Chance.has_chance(player, Chances.NO_REVERSE):

                random_card = random.randrange(6, 8)
                player.chance_cards.append(random_card)
                player.cooldowns.append((Abilities.Hunting, 3))

                ability_used = True
                Logger.log(player.username + " used Hunting +1 (Can't Guard/Can't Reverse)", LogCodes.Ability)

        return ability_used

    # Ability 06 - Attacker
    # chance gained on condition - POSTLUDE
    # condition: damage dealt >= 2
    @staticmethod
    def p_ability06(phase, player):

        ability_used = False
        if phase == match.Phases.POSTLUDE:
            if player.dmg_dealt >= 2:

                Chance.random_chance(player)

                ability_used = True
                Logger.log(player.username + " used Attacker +1 Chance Card", LogCodes.Ability)

        return ability_used

    @staticmethod
    def network_responses(player, opponent, ability_id):

        player_response = None
        opponent_response = None

        # Notify player and opponent about 1 HP gain
        if ability_id == Abilities.Rejuvenation:

            player_response = Network.generate_responseb(
                Flags.GAIN_HP, Flags.ONE_BYTE, 1)

            opponent_response = Network.generate_responseb(
                Flags.OP_GAIN_HP, Flags.ONE_BYTE, 1)

        # Notify player and opponent about new damage modifier
        elif ability_id == Abilities.Critical:

            player_response = Network.generate_responseb(
                Flags.DMG_MODIFIED, Flags.ONE_BYTE, player.modifier)

            opponent_response = Network.generate_responseb(
                Flags.OP_DMG_MODIFIED, Flags.ONE_BYTE, player.modifier)

        # Notify player and opponent about 1 chance card gain
        elif ability_id == Abilities.Gentleman or \
                ability_id == Abilities.Attacker or\
                ability_id == Abilities.Recycling or\
                ability_id == Abilities.Hunting:

            player_response = Network.generate_responseb(
                Flags.GAIN_CHANCE, Flags.ONE_BYTE, player.chance_card)

            opponent_response = Network.generate_responseh(
                Flags.OP_GAIN_CHANCE, Flags.ZERO_BYTE)

        # Notify player and opponent about spotlight ability
        elif ability_id == Abilities.Spotlight:

            player_response = Network.generate_responseh(
                Flags.SPOTLIGHT, Flags.ZERO_BYTE)

            opponent_response = Network.generate_responseh(
                Flags.OP_SPOTLIGHT, Flags.ZERO_BYTE)

        # Notify player and opponent about 2 chance card gain
        elif ability_id == Abilities.Loneliness:

            player_response = Network.generate_responseb(
                Flags.GAIN_CHANCE, Flags.ONE_BYTE, player.pchance_card)

            player_response += Network.generate_responseb(
                Flags.GAIN_CHANCE, Flags.ONE_BYTE, player.chance_card)

            opponent_response = Network.generate_responseh(
                Flags.OP_GAIN_CHANCE, Flags.ZERO_BYTE)

            opponent_response += Network.generate_responseh(
                Flags.OP_GAIN_CHANCE, Flags.ZERO_BYTE)

        if player_response:
            Network.send_data(player.username, player.socket, player_response)

        if opponent_response:
            Network.send_data(opponent.username, opponent.socket, opponent_response)

active_map = {

    Abilities.Rejuvenation: Ability.a_ability00,
    Abilities.Recycling: Ability.a_ability03,
    Abilities.Loneliness: Ability.a_ability04,
    Abilities.Spotlight: Ability.a_ability05,
    Abilities.Critical: Ability.a_ability07
}

passive_map = {

    Abilities.Gentleman: Ability.p_ability01,
    Abilities.Hunting: Ability.p_ability02,
    Abilities.Attacker: Ability.p_ability06
}
