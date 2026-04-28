from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView, View

from foyer.models import MembreFoyer

from .forms import CommentaireForm, NoteForm
from .models import Commentaire, Note
from .services import (
    creer_commentaire,
    get_or_create_note,
    lister_notes_du_foyer,
    marquer_note_consultee,
    mettre_a_jour_contenu,
)


def _membre_du_user(user):
    return (
        MembreFoyer.objects.select_related("foyer")
        .filter(user=user)
        .first()
    )


def _is_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


class _NotesFoyerMixin(LoginRequiredMixin):
    """Garde-fou : l'utilisateur doit appartenir à un foyer.

    Expose `request.membre` et `request.foyer` aux vues filles.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        membre = _membre_du_user(request.user)
        if membre is None:
            return HttpResponseForbidden(
                "Aucun foyer associé à votre compte."
            )
        request.membre = membre
        request.foyer = membre.foyer
        return super().dispatch(request, *args, **kwargs)


class NotesListView(_NotesFoyerMixin, TemplateView):
    template_name = "notes/liste.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ma_note = get_or_create_note(self.request.membre)
        # Marque la note comme consultée AVANT de calculer les commentaires
        # affichés : ouvrir sa note remet à zéro le compteur de non-lus.
        marquer_note_consultee(ma_note)
        notes_avec_commentaires = lister_notes_du_foyer(self.request.foyer)
        ma_note_enrichie = next(
            (n for n in notes_avec_commentaires if n.note.pk == ma_note.pk),
            None,
        )
        notes_autres = [
            n for n in notes_avec_commentaires
            if n.note.membre_id != self.request.membre.pk
        ]
        context["ma_note"] = ma_note_enrichie
        context["notes_autres"] = notes_autres
        context["note_form"] = NoteForm(instance=ma_note)
        context["active_nav"] = "notes"
        return context


class MaNoteView(_NotesFoyerMixin, View):
    template_lecture = "notes/_ma_note.html"
    template_edition = "notes/_ma_note_edition.html"

    def get(self, request):
        if not _is_htmx(request):
            return redirect("notes:liste")
        note = get_or_create_note(request.membre)
        form = NoteForm(instance=note)
        return render(
            request,
            self.template_edition,
            {"note_form": form, "ma_note_brute": note},
        )

    def post(self, request):
        note = get_or_create_note(request.membre)
        form = NoteForm(request.POST, instance=note)
        if not form.is_valid():
            return render(
                request,
                self.template_edition,
                {"note_form": form, "ma_note_brute": note},
                status=400,
            )
        note = mettre_a_jour_contenu(note, form.cleaned_data["contenu"])
        # Recalcule la liste actifs/orphelins pour ré-afficher la note en
        # mode lecture après l'édition (les commentaires existants peuvent
        # avoir basculé entre actifs et orphelins).
        from .services import lister_notes_du_foyer
        enrichie = next(
            (
                n for n in lister_notes_du_foyer(request.foyer)
                if n.note.pk == note.pk
            ),
            None,
        )
        return render(
            request,
            self.template_lecture,
            {"ma_note": enrichie},
        )


class CommentaireCreateView(_NotesFoyerMixin, View):
    template_commentaire = "notes/_commentaire.html"
    template_form_inline = "notes/_commentaire_form_inline.html"

    def post(self, request, note_id):
        note = get_object_or_404(
            Note.objects.select_related("membre__foyer"),
            pk=note_id,
            membre__foyer=request.foyer,
        )
        if note.membre_id == request.membre.pk:
            return HttpResponseForbidden(
                "On ne commente pas sa propre note."
            )
        form = CommentaireForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_form_inline,
                {"form": form, "note": note},
                status=400,
            )
        commentaire = creer_commentaire(
            note=note,
            auteur=request.user,
            extrait=form.cleaned_data["extrait"],
            contenu=form.cleaned_data["contenu"],
        )
        response = render(
            request,
            self.template_commentaire,
            {"commentaire": commentaire, "note": note},
        )
        response["HX-Trigger"] = "commentaires-mis-a-jour"
        return response


class CommentaireDeleteView(_NotesFoyerMixin, View):
    def post(self, request, commentaire_id):
        commentaire = get_object_or_404(
            Commentaire.objects.select_related(
                "note__membre__foyer", "auteur"
            ),
            pk=commentaire_id,
            note__membre__foyer=request.foyer,
        )
        if commentaire.auteur_id != request.user.pk:
            return HttpResponseForbidden(
                "Seul l'auteur peut supprimer son commentaire."
            )
        commentaire.delete()
        # Réponse vide : HTMX swappe par rien, retirant le commentaire du DOM.
        response = HttpResponse("")
        response["HX-Trigger"] = "commentaires-mis-a-jour"
        return response
