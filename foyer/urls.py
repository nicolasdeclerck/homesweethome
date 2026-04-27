from django.urls import path

from . import views

app_name = "foyer"

urlpatterns = [
    path("", views.MonFoyerView.as_view(), name="mon-foyer"),
    path(
        "invitations/",
        views.InvitationCreateView.as_view(),
        name="invitation-create",
    ),
    path(
        "invitations/liste/",
        views.InvitationsListeView.as_view(),
        name="invitation-liste",
    ),
    path(
        "invitations/<int:pk>/lien/",
        views.InvitationLinkView.as_view(),
        name="invitation-lien",
    ),
    path(
        "invitations/<int:pk>/annuler/",
        views.InvitationCancelView.as_view(),
        name="invitation-annuler",
    ),
    path(
        "invitations/accepter/<str:token>/",
        views.AccepterInvitationView.as_view(),
        name="invitation-accepter",
    ),
]
