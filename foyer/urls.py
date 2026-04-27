from django.urls import path

from . import views

app_name = "foyer"

urlpatterns = [
    path("", views.MonFoyerView.as_view(), name="mon-foyer"),
]
