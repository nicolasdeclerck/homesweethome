from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import TemplateView, View

from foyer.models import MembreFoyer

from .forms import ActiviteCreationForm
from .services import creer_activite, lister_activites_par_categorie


def _foyer_du_user(user):
    membre = (
        MembreFoyer.objects.select_related("foyer")
        .filter(user=user)
        .first()
    )
    return membre.foyer if membre else None


class _ActivitesFoyerMixin(LoginRequiredMixin):
    """Garde-fou : l'utilisateur doit appartenir à un foyer.

    Expose `request.foyer` aux vues filles. En pratique, le signal
    `post_save(User)` crée toujours un foyer pour chaque user, mais on
    garde ce filet de sécurité (équivalent du pattern `_CreateurFoyerRequiredMixin`).
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        foyer = _foyer_du_user(request.user)
        if foyer is None:
            return HttpResponseForbidden(
                "Aucun foyer associé à votre compte."
            )
        request.foyer = foyer
        return super().dispatch(request, *args, **kwargs)


def _contexte_liste(foyer):
    """Contexte partagé entre la vue page et le fragment de liste."""
    activites_par_categorie = lister_activites_par_categorie(foyer)
    nb_activites = sum(len(v) for v in activites_par_categorie.values())
    return {
        "foyer": foyer,
        "activites_par_categorie": activites_par_categorie,
        "categories_existantes": list(
            foyer.categories.order_by("nom").values_list("nom", flat=True)
        ),
        "nb_activites": nb_activites,
    }


class ActivitesListView(_ActivitesFoyerMixin, TemplateView):
    template_name = "activites/liste.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexte_liste(self.request.foyer))
        context["form"] = ActiviteCreationForm()
        context["active_nav"] = "activites"
        return context


class ActiviteCreateView(_ActivitesFoyerMixin, View):
    template_form = "activites/_activite_form.html"

    def get(self, request):
        return redirect("activites:activite-liste")

    def post(self, request):
        form = ActiviteCreationForm(request.POST)
        is_htmx = request.headers.get("HX-Request") == "true"

        if not form.is_valid():
            if is_htmx:
                return render(
                    request,
                    self.template_form,
                    {
                        "form": form,
                        "categories_existantes": list(
                            request.foyer.categories.order_by("nom").values_list(
                                "nom", flat=True
                            )
                        ),
                    },
                    status=400,
                )
            context = _contexte_liste(request.foyer)
            context["form"] = form
            context["active_nav"] = "activites"
            return render(request, "activites/liste.html", context, status=400)

        creer_activite(
            foyer=request.foyer,
            titre=form.cleaned_data["titre"],
            categorie_nom=form.cleaned_data["categorie_nom"],
        )

        if is_htmx:
            response = render(
                request,
                self.template_form,
                {
                    "form": ActiviteCreationForm(),
                    "categories_existantes": list(
                        request.foyer.categories.order_by("nom").values_list(
                            "nom", flat=True
                        )
                    ),
                },
            )
            response["HX-Trigger"] = "activites-mises-a-jour"
            return response

        messages.success(request, "Activité ajoutée.")
        return redirect(reverse("activites:activite-liste"))


class ActivitesListeFragmentView(_ActivitesFoyerMixin, View):
    template_liste = "activites/_activites_liste.html"

    def get(self, request):
        contexte = _contexte_liste(request.foyer)
        # Active le span OOB qui rafraîchit le compteur du sous-titre.
        contexte["oob_compteur"] = True
        return render(request, self.template_liste, contexte)
