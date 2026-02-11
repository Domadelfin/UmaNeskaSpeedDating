from django import forms
from .models import Participant

class ParticipantJoinForm(forms.ModelForm):
    
    preferred_gender = forms.ChoiceField(
        choices = Participant.InterestedIn.choices
    )

    class Meta:
        model = Participant
        fields = ["nickname", "gender_identity"]
