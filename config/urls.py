from django.contrib import admin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import include, path
from django.views.generic import TemplateView


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "home.html"


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", HomeView.as_view(), name="home"),
    path("", include("comptes.urls")),
]
