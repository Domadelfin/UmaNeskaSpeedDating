from django.contrib import admin
from .models import Event, Participant, Question, Answer
# Register your models here.
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'status', 'created_by', 'created_at']
    list_filter = ("status",)
    search_fields = ("name", "code")
    ordering = ("-created_at",)

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "nickname",
        "event",
        "gender_identity",
        "answers_complete",
        "matched_with",
        "created_at",
    )
    list_filter = ("event", "gender_identity", "answers_complete")
    search_fields = ("nickname",)
    autocomplete_fields = ("matched_with",)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "type")
    list_filter = ("type",)
    search_fields = ("text",)

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("participant", "question", "value")
    search_fields = ("participant__nickname", "value")