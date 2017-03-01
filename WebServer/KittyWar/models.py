from django.db import models
from django.contrib.auth.models import User


class AbilityCards(models.Model):

    CARD_PHASES = (
        (0, 'Any'),
        (1, 'Prelude'),
        (2, 'Enacting strategies'),
        (3, 'Showing Cards'),
        (4, 'Strategy settlement'),
        (5, 'Postlude'),
    )

    ability_id = models.PositiveIntegerField(default=0, primary_key=True)

    title = models.CharField(max_length=32)
    description = models.CharField(max_length=1024)

    phase = models.PositiveIntegerField(1, choices=CARD_PHASES, default=0)
    cooldown = models.PositiveIntegerField(default=0)


class CatCard(models.Model):

    cat_id = models.PositiveIntegerField(default=0, primary_key=True)

    title = models.CharField(max_length=32)
    description = models.CharField(max_length=1024)

    health = models.PositiveIntegerField(default=0)
    default = models.PositiveIntegerField(default=0)
    ability_id = models.PositiveIntegerField(default=0)


class BasicCards(models.Model):

    basic_id = models.PositiveIntegerField(default=0, primary_key=True)

    title = models.CharField(max_length=32)
    description = models.CharField(max_length=1024)
    flavor = models.CharField(max_length=1024)


class ChanceCards(models.Model):

    chance_id = models.PositiveIntegerField(default=0, primary_key=True)

    title = models.CharField(max_length=32)
    type = models.CharField(max_length=32)
    description = models.CharField(max_length=1024)

    basic_id = models.PositiveIntegerField(default=0)


class UserProfile(models.Model):
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    token = models.CharField(max_length=24)

    matches = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    loss = models.PositiveIntegerField(default=0)
    draw = models.PositiveIntegerField(default=0)
    cats = models.ManyToManyField(CatCard)

    def logged_in(self):

        if self.token != '':
            return True
        return False
