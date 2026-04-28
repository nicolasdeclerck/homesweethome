from django.contrib import admin
from django.urls import include, path, reverse
from django.views.generic import RedirectView

from .health import health


class RootRedirectView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return reverse("foyer:mon-foyer")
        return reverse("comptes:connexion")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("", RootRedirectView.as_view(), name="root"),
    path("foyer/", include("foyer.urls")),
    path("activites/", include("activites.urls")),
    path("evaluations/", include("evaluations.urls")),
    path("", include("comptes.urls")),
]
