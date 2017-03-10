from enum import Enum, IntEnum


class Moves(IntEnum):

    @staticmethod
    def valid_move(move):
        return move in list(map(int, Moves))

    # Handles the user selecting a move
    @staticmethod
    def select_move(player, move):

        # Make sure the move is valid and they have not already selected a move
        valid_move = Moves.valid_move(move) and not player.move

        if valid_move:
            player.move = move

        return valid_move

    PURR = 0
    GUARD = 1
    SCRATCH = 2
    SKIP = 3


class Cats(Enum):

    @staticmethod
    def identify_cat(cat_id):

        if cat_id == Cats.Persian.id:
            return Cats.Persian

        elif cat_id == Cats.Ragdoll.id:
            return Cats.Ragdoll

        elif cat_id == Cats.Maine.id:
            return Cats.Maine

        else:
            return Cats.Persian

    # Handles the user selecting a cat for the match
    @staticmethod
    def select_cat(player, cat_id):

        # Verify user can select the cat they have
        valid_cat = False

        selected_cat = Cats.identify_cat(cat_id)
        for owned_cat in player.cats:

            if selected_cat.id == owned_cat:

                player.cat = selected_cat
                valid_cat = True
                break

        return valid_cat

    # (ID, HP, ABILITY)
    Persian =    (0,  8, 0)
    Ragdoll =    (1, 10, 1)
    Maine =      (2, 10, 2)
    Shorthair =  (3, 10, 3)
    Siamese =    (4, 10, 4)
    Abyssinian = (5, 10, 5)

    def __init__(self, id, hp, ability_id):
        self.id = id
        self.hp = hp
        self.ability_id = ability_id
