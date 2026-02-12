from django.contrib import admin
from .models import Event, Participant, Question, Answer, Option
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
        "matched_with_secondary",
        "created_at",
    )
    list_filter = ("event", "gender_identity", "answers_complete")
    search_fields = ("nickname",)
    autocomplete_fields = ("matched_with", "matched_with_secondary")
    actions = ("clear_matches",)

    @admin.action(description="Clear match relations for selected participants")
    def clear_matches(self, request, queryset):
        queryset.update(matched_with=None, matched_with_secondary=None)

class OptionInline(admin.TabularInline):
    model = Option
    extra = 4

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "type", "weight", "is_scored")
    list_filter = ("type", "is_scored")
    search_fields = ("text",)
    inlines = [OptionInline]

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("participant", "question", "value")
    search_fields = ("participant__nickname", "value")
