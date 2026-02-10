from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("questions/", views.questions, name="questions"),
    path("admin/", views.admin, name="admin"),
    path("admin/events/<uuid:event_id>/status/", views.admin_update_status, name="admin_update_status"),
    path("admin/events/<uuid:event_id>/countdown/", views.admin_reveal_countdown, name="admin_reveal_countdown"),
    path("resume/", views.resume, name="resume"),
    path("profile/", views.profile, name="profile"),
]
