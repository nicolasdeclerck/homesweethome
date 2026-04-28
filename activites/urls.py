from django.urls import path

from . import views

app_name = "activites"

urlpatterns = [
    path("", views.ActivitesListView.as_view(), name="activite-liste"),
    path(
        "ajouter/",
        views.ActiviteCreateView.as_view(),
        name="activite-create",
    ),
    path(
        "<int:activite_id>/modifier/",
        views.ActiviteUpdateView.as_view(),
        name="activite-modifier",
    ),
    path(
        "liste-fragment/",
        views.ActivitesListeFragmentView.as_view(),
        name="activite-liste-fragment",
    ),
]
