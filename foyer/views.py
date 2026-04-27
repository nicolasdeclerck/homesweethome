from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .services import get_or_create_foyer_for_user


class MonFoyerView(LoginRequiredMixin, TemplateView):
    template_name = "foyer/mon_foyer.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        foyer = get_or_create_foyer_for_user(self.request.user)
        context["foyer"] = foyer
        context["membres"] = foyer.membres.select_related("user").all()
        return context
