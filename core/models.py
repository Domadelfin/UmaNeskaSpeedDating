import uuid
from django.conf import settings
from django.db import models


class Event(models.Model):
    STATUS_CHOICES = [
        ("collecting", "Collecting"),
        ("matching", "Matching"),
        ("revealed", "Revealed"),
        ("closed", "Closed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="events",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)


class Participant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class GenderIdentity(models.TextChoices):
        WOMAN = "woman", "Woman"
        MAN = "man", "Man"
        NONBINARY = "nonbinary", "Non-binary"
        TRANS_WOMAN = "trans_woman", "Trans woman"
        TRANS_MAN = "trans_man", "Trans man"
        GENDERQUEER = "genderqueer", "Genderqueer"
        AGENDER = "agender", "Agender"
        OTHER = "other", "Another identity"

    class InterestedIn(models.TextChoices):
        WOMEN = "women", "Women"
        MEN = "men", "Men"
        NONBINARY = "nonbinary", "Non-binary people"
        TRANS_WOMEN = "trans_women", "Trans women"
        TRANS_MEN = "trans_men", "Trans men"
        ANY = "any", "Anyone"

    class Bracelet(models.TextChoices):
        RED = "red", "Red - Single & open to dating"
        GOLD = "gold", "Gold - Queer"
        GREEN = "green", "Green - Bi / Pan"
        PINK = "pink", "Pink - Femme-leaning"
        BLUE = "blue", "Blue - Masc-leaning"
        SILVER = "silver", "Silver - Taken / here socially"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="participants",
    )

    nickname = models.CharField(max_length=100)
    gender_identity = models.CharField(max_length=50, choices=GenderIdentity.choices)
    interested_in = models.JSONField()
    bracelet = models.CharField(max_length=20, choices=Bracelet.choices, default=Bracelet.RED)

    age = models.IntegerField(null=True, blank=True)

    answers_complete = models.BooleanField(default=False)

    matched_with = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="matched_by",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "nickname"],
                name="unique_nickname_per_event",
            )
        ]

    @property
    def interested_in_labels(self):
        values = self.interested_in or []
        labels = []
        for value in values:
            try:
                labels.append(self.InterestedIn(value).label)
            except ValueError:
                labels.append(str(value))
        return labels


class Question(models.Model):
    
    QUESTION_TYPES = [
        ("text", "Text"),
        ("choice", "Single Choice"),
        ("multiple_choice", "Multiple Choice"),
        ("dropdown", "Dropdown"),
        ("number", "Number"),
        ("date", "Date"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    text = models.TextField()

    type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    weight = models.FloatField(default=1.0)
    is_scored = models.BooleanField(default=True)

    def __str__(self):
        return self.text[:60]


class Answer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="answers",
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answers",
    )

    value = models.TextField()
    value_json = models.JSONField(null=True, blank=True)

class Option(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    question = models.ForeignKey(
        Question,
        related_name="options",
        on_delete=models.CASCADE
    )

    text = models.CharField(max_length=200)
    value = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.text
