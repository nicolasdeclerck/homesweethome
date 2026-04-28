from django.urls import path

from . import views

app_name = "planification"

urlpatterns = [
    path("", views.PeriodesListView.as_view(), name="periode-liste"),
    path(
        "ajouter/",
        views.PeriodeCreateView.as_view(),
        name="periode-create",
    ),
    path(
        "liste-fragment/",
        views.PeriodesListeFragmentView.as_view(),
        name="periode-liste-fragment",
    ),
    path(
        "<int:periode_id>/",
        views.PeriodeDetailView.as_view(),
        name="periode-detail",
    ),
    path(
        "<int:periode_id>/affectations-fragment/",
        views.AffectationsListeFragmentView.as_view(),
        name="affectations-liste-fragment",
    ),
    path(
        "<int:periode_id>/affectations/ajouter/",
        views.AffectationCreateView.as_view(),
        name="affectation-create",
    ),
    path(
        "affectations/<int:affectation_id>/supprimer/",
        views.AffectationDeleteView.as_view(),
        name="affectation-delete",
    ),
]
