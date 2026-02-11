from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Prefetch, Case, When, Value, IntegerField
from django.http import JsonResponse
import uuid
import networkx as nx

from . import models

def home(request):
    event = models.Event.objects.filter(status="collecting").first()
    gender_choices = models.Participant.GenderIdentity.choices
    interest_choices = models.Participant.InterestedIn.choices
    bracelet_choices = models.Participant.Bracelet.choices

    if not event:
        return render(request, "core/home.html", {
            "errors": {"event": "No active event right now."},
            "form": {
                "name": "",
                "gender": "",
                "preferred_gender": "",
                "bracelet": "",
            },
            "gender_choices": gender_choices,
            "interest_choices": interest_choices,
            "bracelet_choices": bracelet_choices,
        })
    
    if request.method == "POST":
        # Grab and normalise input
        nickname = request.POST.get("name", "").strip()
        gender = request.POST.get("gender", "").strip()
        preferred_gender = request.POST.get("preferred_gender", "").strip()
        bracelet = request.POST.get("bracelet", "").strip()

        errors = {}

        # Field‑level validation
        if not nickname:
            errors["name"] = "Please enter a display name."
        if not gender:
            errors["gender"] = "Please select how you identify."
        if not preferred_gender:
            errors["preferred_gender"] = "Please select who you want to meet."
        if not bracelet:
            errors["bracelet"] = "Please select your bracelet color."

        if not errors:
            allowed_genders = set(models.Participant.GenderIdentity.values)
            allowed_interests = set(models.Participant.InterestedIn.values)
            allowed_bracelets = set(models.Participant.Bracelet.values)
            if gender not in allowed_genders:
                errors["gender"] = "Please select a valid identity."
            if preferred_gender not in allowed_interests:
                errors["preferred_gender"] = "Please select a valid preference."
            if bracelet not in allowed_bracelets:
                errors["bracelet"] = "Please select a valid bracelet."

        if not errors:
            # Store interested_in as a list to match the questions template join
            interested_in = [preferred_gender]

            try:
                participant = models.Participant.objects.create(
                    event=event,
                    nickname=nickname,
                    gender_identity=gender,
                    interested_in=interested_in,
                    bracelet=bracelet,
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
                    "bracelet": "",
                },
                "gender_choices": gender_choices,
                "interest_choices": interest_choices,
                "bracelet_choices": bracelet_choices,
            },
        )
    
    return render(request, "core/home.html", {
        "form": {},
        "gender_choices": gender_choices,
        "interest_choices": interest_choices,
        "bracelet_choices": bracelet_choices,
    })
                


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
    event_stats = []
    for event in events:
        participants = list(event.participants.all())
        answered_count = sum(1 for p in participants if p.answers_complete)
        event_stats.append({
            "event": event,
            "participants_count": len(participants),
            "answered_count": answered_count,
        })
    return render(request, "core/admin.html", {"event_stats": event_stats})


def admin_status(request):
    events = models.Event.objects.prefetch_related("participants").order_by("-created_at")
    payload = []
    for event in events:
        participants = list(event.participants.all())
        answered_count = sum(1 for p in participants if p.answers_complete)
        payload.append({
            "id": str(event.id),
            "status": event.status,
            "status_label": event.get_status_display(),
            "participants_count": len(participants),
            "answered_count": answered_count,
        })
    return JsonResponse({"events": payload})


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
    match_secondary = participant.matched_with_secondary

    return render(
        request,
        "core/profile.html",
        {
            "participant": participant,
            "event": event,
            "match": match,
            "match_secondary": match_secondary,
        },
    )


def profile_status(request):
    participant_id = request.session.get("participant_id")
    if not participant_id:
        return JsonResponse({"redirect": reverse("resume")}, status=401)

    participant = get_object_or_404(models.Participant, id=uuid.UUID(participant_id))
    if not participant.answers_complete:
        return JsonResponse({"redirect": reverse("questions")}, status=403)

    event = participant.event
    match = participant.matched_with
    match_secondary = participant.matched_with_secondary

    return JsonResponse({
        "event_status": event.status,
        "event_status_label": event.get_status_display(),
        "match_nickname": match.nickname if match else None,
        "match_secondary_nickname": match_secondary.nickname if match_secondary else None,
    })

   
   


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


def admin_run_matching(request, event_id):
    if request.method != "POST":
        return redirect(reverse("admin"))

    event = get_object_or_404(models.Event, id=event_id)

    if event.status == "collecting":
        event.status = "matching"
        event.save(update_fields=["status"])

    participants = list(
        models.Participant.objects.filter(
            event=event,
            answers_complete=True,
            bracelet__in=[
                models.Participant.Bracelet.RED,
                models.Participant.Bracelet.GOLD,
                models.Participant.Bracelet.GREEN,
                models.Participant.Bracelet.PINK,
                models.Participant.Bracelet.BLUE,
            ],
        ).prefetch_related(
            "answers__question",
        )
    )

    def normalize_gender(identity):
        if identity == models.Participant.GenderIdentity.TRANS_WOMAN:
            return models.Participant.GenderIdentity.WOMAN
        if identity == models.Participant.GenderIdentity.TRANS_MAN:
            return models.Participant.GenderIdentity.MAN
        return identity

    def preference_allows(preference, identity):
        if preference == models.Participant.InterestedIn.ANY:
            return True
        if preference == models.Participant.InterestedIn.WOMEN:
            return normalize_gender(identity) == models.Participant.GenderIdentity.WOMAN
        if preference == models.Participant.InterestedIn.MEN:
            return normalize_gender(identity) == models.Participant.GenderIdentity.MAN
        if preference == models.Participant.InterestedIn.NONBINARY:
            return normalize_gender(identity) == models.Participant.GenderIdentity.NONBINARY
        if preference == models.Participant.InterestedIn.TRANS_WOMEN:
            return identity == models.Participant.GenderIdentity.TRANS_WOMAN
        if preference == models.Participant.InterestedIn.TRANS_MEN:
            return identity == models.Participant.GenderIdentity.TRANS_MAN
        return False

    def is_compatible(a, b):
        a_prefs = a.interested_in or []
        b_prefs = b.interested_in or []
        return (
            any(preference_allows(pref, b.gender_identity) for pref in a_prefs) and
            any(preference_allows(pref, a.gender_identity) for pref in b_prefs)
        )

    def answer_similarity(a_answer, b_answer, question):
        if not a_answer or not b_answer:
            return 0.0

        if question.type == "multiple_choice":
            a_vals = set(a_answer.value_json or [])
            b_vals = set(b_answer.value_json or [])
            if not a_vals and not b_vals:
                return 0.0
            intersection = len(a_vals & b_vals)
            union = len(a_vals | b_vals)
            return intersection / union if union else 0.0

        a_val = (a_answer.value or "").strip().lower()
        b_val = (b_answer.value or "").strip().lower()
        return 1.0 if a_val and a_val == b_val else 0.0

    answers_by_participant = {}
    for participant in participants:
        answers_by_participant[participant.id] = {
            ans.question_id: ans for ans in participant.answers.all()
        }

    graph = nx.Graph()
    participant_by_id = {}
    for participant in participants:
        graph.add_node(participant.id, participant=participant)
        participant_by_id[participant.id] = participant

    for i, a in enumerate(participants):
        for b in participants[i + 1:]:
            if not is_compatible(a, b):
                continue

            score = 0.0
            a_answers = answers_by_participant.get(a.id, {})
            b_answers = answers_by_participant.get(b.id, {})
            for question_id, a_answer in a_answers.items():
                question = a_answer.question
                if not question.is_scored:
                    continue
                b_answer = b_answers.get(question_id)
                similarity = answer_similarity(a_answer, b_answer, question)
                score += similarity * question.weight

            graph.add_edge(a.id, b.id, weight=score)

    matching = nx.algorithms.matching.max_weight_matching(graph, maxcardinality=True)

    with transaction.atomic():
        models.Participant.objects.filter(event=event).update(
            matched_with=None,
            matched_with_secondary=None,
        )
        for a_id, b_id in matching:
            a = participant_by_id.get(a_id)
            b = participant_by_id.get(b_id)
            if not a or not b:
                continue
            a.matched_with = b
            b.matched_with = a
            a.save(update_fields=["matched_with"])
            b.save(update_fields=["matched_with"])

        matched_ids = set()
        for a_id, b_id in matching:
            matched_ids.add(a_id)
            matched_ids.add(b_id)

        unmatched = [p for p in participants if p.id not in matched_ids]

        if unmatched:
            for p in unmatched:
                best = None
                best_score = -1

                for candidate in participants:
                    if candidate.id == p.id:
                        continue
                    if not is_compatible(p, candidate):
                        continue

                    candidate_answers = answers_by_participant.get(candidate.id, {})
                    p_answers = answers_by_participant.get(p.id, {})
                    score = 0.0
                    for question_id, p_answer in p_answers.items():
                        question = p_answer.question
                        if not question.is_scored:
                            continue
                        c_answer = candidate_answers.get(question_id)
                        similarity = answer_similarity(p_answer, c_answer, question)
                        score += similarity * question.weight

                    if score > best_score:
                        best_score = score
                        best = candidate

                if best:
                    if best.matched_with is None:
                        best.matched_with = p
                        best.save(update_fields=["matched_with"])
                    elif best.matched_with_secondary is None:
                        best.matched_with_secondary = p
                        best.save(update_fields=["matched_with_secondary"])

                    if p.matched_with is None:
                        p.matched_with = best
                        p.save(update_fields=["matched_with"])
                    elif p.matched_with_secondary is None:
                        p.matched_with_secondary = best
                        p.save(update_fields=["matched_with_secondary"])

    return redirect(reverse("admin"))
