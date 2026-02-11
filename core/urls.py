from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("questions/", views.questions, name="questions"),
    path("host/", views.admin, name="admin"),
    path("host/status/", views.admin_status, name="admin_status"),
    path("host/events/<uuid:event_id>/status/", views.admin_update_status, name="admin_update_status"),
    path("host/events/<uuid:event_id>/match/", views.admin_run_matching, name="admin_run_matching"),
    path("resume/", views.resume, name="resume"),
    path("profile/", views.profile, name="profile"),
    path("profile/status/", views.profile_status, name="profile_status"),
]
