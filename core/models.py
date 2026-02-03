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

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="participants",
    )

    nickname = models.CharField(max_length=100)
    gender_identity = models.CharField(max_length=50)
    interested_in = models.JSONField()

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


class Question(models.Model):

    QUESTION_TYPES = [
        ("text", "Text"),
        ("choice", "Single Choice"),
        ("multiple_choice", "Multiple Choice"),
        ("number", "Number"),
        ("date", "Date"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    text = models.TextField()
    type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    options = models.JSONField(null=True, blank=True)


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
