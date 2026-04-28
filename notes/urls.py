from django.urls import path

from . import views

app_name = "notes"

urlpatterns = [
    path("", views.NotesListView.as_view(), name="liste"),
    path(
        "ma-note/",
        views.MaNoteView.as_view(),
        name="ma-note",
    ),
    path(
        "<int:note_id>/commentaires/",
        views.CommentaireCreateView.as_view(),
        name="commentaire-create",
    ),
    path(
        "commentaires/<int:commentaire_id>/supprimer/",
        views.CommentaireDeleteView.as_view(),
        name="commentaire-delete",
    ),
]
