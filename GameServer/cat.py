from enum import Enum, IntEnum


class Moves(IntEnum):

    @staticmethod
    def valid_move(move):
        return move in list(map(int, Moves))

    # Handles the user selecting a move
    @staticmethod
    def select_move(player, move):

        valid_move = Moves.valid_move(move)
        if valid_move:
            player.move = move

        return valid_move

    PURR = 0
    GUARD = 1
    SCRATCH = 2
    SKIP = 3


class Cats(Enum):

    @staticmethod
    def get_hp(cat_id):

        if cat_id == 0:
            return Cats.Persian.hp
        elif cat_id == 1:
            return Cats.Ragdoll.hp
        elif cat_id == 2:
            return Cats.Maine.hp

    @staticmethod
    def get_ability(cat_id):

        if cat_id == 0:
            return Cats.Persian.ability_id
        elif cat_id == 1:
            return Cats.Ragdoll.ability_id
        elif cat_id == 2:
            return Cats.Maine.ability_id

    # Handles the user selecting a cat for the match
    @staticmethod
    def select_cat(player, cat_id):

        # Verify user can select the cat they have
        valid_cat = False

        for cat in player.cats:

            if cat == cat_id:

                player.cat = cat
                valid_cat = True
                break

        return valid_cat

    Persian = (8, 0)
    Ragdoll = (10, 1)
    Maine = (12, 2)

    def __init__(self, hp, ability_id):
        self.hp = hp
        self.ability_id = ability_id
