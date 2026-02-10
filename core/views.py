from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Prefetch, Case, When, Value, IntegerField
import uuid

from . import models

def home(request):
    event = models.Event.objects.filter(status="collecting").first()

    if not event:
        return render(request, "core/home.html", {
            "errors": {"event": "No active event right now."},
            "form": {
                "name": "",
                "gender": "",
                "preferred_gender": "",
            }
        })
    
    if request.method == "POST":
        # Grab and normalise input
        nickname = request.POST.get("name", "").strip()
        gender = request.POST.get("gender", "").strip()
        preferred_gender = request.POST.get("preferred_gender", "").strip()

        errors = {}

        # Field‑level validation
        if not nickname:
            errors["name"] = "Please enter a display name."
        if not gender:
            errors["gender"] = "Please select how you identify."
        if not preferred_gender:
            errors["preferred_gender"] = "Please select who you want to meet."

        if not errors:
            # Store interested_in as a list to match the questions template join
            interested_in = [preferred_gender]

            try:
                participant = models.Participant.objects.create(
                    event=event,
                    nickname=nickname,
                    gender_identity=gender,
                    interested_in=interested_in,
                )
            except IntegrityError:
                # Nickname taken for this event
                errors["name"] = "That nickname is already taken for this event."
            else:
                # All good – persist identity in the session and go to questions
                request.session["participant_id"] = str(participant.id)
                request.session["session_id"] = str(event.id)

                return redirect(reverse("questions"))

        # Either initial validation failed or uniqueness check failed;
        # re‑render with errors and the values the user entered.
        return render(
            request,
            "core/home.html",
            {
                "errors": errors,
                "form": {
                    "name": "",
                    "gender": "",
                    "preferred_gender": "",
                },
            },
        )
    
    return render(request, "core/home.html", {"form": {}})
                


def questions(request):
    participant_id = request.session.get("participant_id")
    
    if not participant_id:
        return redirect(reverse("home"))

    participant = get_object_or_404(models.Participant, id=uuid.UUID(participant_id))

    questions = models.Question.objects.prefetch_related(
        Prefetch("options", queryset=models.Option.objects.order_by("order"))
    ).order_by(
        Case(When(type="dropdown", then=Value(0)), default=Value(1), output_field=IntegerField()),
        "id",
    )

    if request.method == "POST":
        with transaction.atomic():
            participant.answers.all().delete()

            answers_to_create = []
            for question in questions:
                field_name = f"question_{question.id}"

                if question.type == "multiple_choice":
                    values = request.POST.getlist(f"{field_name}[]") or request.POST.getlist(field_name)
                    value_text = ", ".join(values)
                    answers_to_create.append(models.Answer(
                        participant=participant,
                        question=question,
                        value=value_text,
                        value_json=values if values else None,
                    ))
                else:
                    value = (request.POST.get(field_name) or "").strip()
                    answers_to_create.append(models.Answer(
                        participant=participant,
                        question=question,
                        value=value,
                    ))

            if answers_to_create:
                models.Answer.objects.bulk_create(answers_to_create)

            participant.answers_complete = True
            participant.save(update_fields=["answers_complete"])

        return redirect(reverse("profile"))

    return render(
        request,
        "core/questions.html",
        {
            "participant": participant,
            "questions": questions,
        },
    )

def admin(request):
    events = models.Event.objects.prefetch_related("participants").order_by("-created_at")
    return render(request, "core/admin.html", {"events": events})


def resume(request):
    errors = {}

    if request.method == "POST":
        code = request.POST.get("event_code", "").strip()
        nickname = request.POST.get("nickname", "").strip()

        if not code:
            errors["event_code"] = "Please enter the event code."
        if not nickname:
            errors["nickname"] = "Please enter your nickname."

        if not errors:
            event = models.Event.objects.filter(code__iexact=code).first()
            if not event:
                errors["event_code"] = "Event not found."
            else:
                participant = models.Participant.objects.filter(
                    event=event,
                    nickname__iexact=nickname,
                ).first()
                if not participant:
                    errors["nickname"] = "Nickname not found for this event."
                else:
                    request.session["participant_id"] = str(participant.id)
                    request.session["session_id"] = str(event.id)
                    if not participant.answers_complete:
                        return redirect(reverse("questions"))
                    return redirect(reverse("profile"))

    return render(
        request,
        "core/resume.html",
        {
            "errors": errors,
            "form": {
                "event_code": request.POST.get("event_code", "") if request.method == "POST" else "",
                "nickname": request.POST.get("nickname", "") if request.method == "POST" else "",
            },
        },
    )


def profile(request):
    participant_id = request.session.get("participant_id")
    if not participant_id:
        return redirect(reverse("resume"))

    participant = get_object_or_404(models.Participant, id=uuid.UUID(participant_id))
    if not participant.answers_complete:
        return redirect(reverse("questions"))

    event = participant.event
    match = participant.matched_with

    return render(
        request,
        "core/profile.html",
        {
            "participant": participant,
            "event": event,
            "match": match,
        },
    )


def admin_update_status(request, event_id):
    if request.method != "POST":
        return redirect(reverse("admin"))

    event = get_object_or_404(models.Event, id=event_id)
    new_status = request.POST.get("status", "").strip()
    valid_statuses = {choice[0] for choice in models.Event.STATUS_CHOICES}

    transitions = {
        "collecting": {"matching", "closed"},
        "matching": {"revealed", "closed"},
        "revealed": {"closed"},
        "closed": set(),
    }

    if new_status in valid_statuses and new_status != event.status:
        allowed_next = transitions.get(event.status, set())
        if new_status in allowed_next:
            event.status = new_status
            event.save(update_fields=["status"])

    return redirect(reverse("admin"))


def admin_reveal_countdown(request, event_id):
    event = get_object_or_404(models.Event, id=event_id)
    return render(request, "core/countdown.html", {"event": event})
