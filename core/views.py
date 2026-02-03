from django.shortcuts import render, redirect
from django.urls import reverse


def home(request):
    """
    Participant entry point.
    Collect basic identifiers before sending them to the questions flow.
    """
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        gender = request.POST.get("gender", "").strip()
        preferred_gender = request.POST.get("preferred_gender", "").strip()

        errors = {}
        if not name:
            errors["name"] = "Please enter a display name."
        if not gender:
            errors["gender"] = "Please select how you identify."
        if not preferred_gender:
            errors["preferred_gender"] = "Please select who you’d like to be matched with."

        if not errors:
            request.session["participant"] = {
                "name": name,
                "gender": gender,
                "preferred_gender": preferred_gender,
            }
            return redirect(reverse("questions"))

        context = {
            "errors": errors,
            "form": {
                "name": name,
                "gender": gender,
                "preferred_gender": preferred_gender,
            },
        }
        return render(request, "core/home.html", context)

    # GET – prefill from session if they’ve been here before
    participant = request.session.get("participant", {})
    context = {
        "form": {
            "name": participant.get("name", ""),
            "gender": participant.get("gender", ""),
            "preferred_gender": participant.get("preferred_gender", ""),
        }
    }
    return render(request, "core/home.html", context)


def questions(request):
    """
    Placeholder questions page that will later show the active question.
    For now, it just greets the participant using their stored identifiers.
    """
    participant = request.session.get("participant")
    if not participant:
        # If someone lands here directly, send them to the identifier step first.
        return redirect(reverse("home"))

    return render(request, "core/questions.html", {"participant": participant})