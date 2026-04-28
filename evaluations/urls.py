from django.urls import path

from . import views

app_name = "evaluations"

urlpatterns = [
    path(
        "<int:activite_id>/",
        views.EvaluationView.as_view(),
        name="activite-evaluer",
    ),
]
