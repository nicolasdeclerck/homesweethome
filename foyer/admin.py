from django.contrib import admin

from .models import Foyer, MembreFoyer


@admin.register(Foyer)
class FoyerAdmin(admin.ModelAdmin):
    list_display = ("nom", "date_creation")
    search_fields = ("nom",)
    ordering = ("-date_creation",)


@admin.register(MembreFoyer)
class MembreFoyerAdmin(admin.ModelAdmin):
    list_display = ("user", "foyer", "date_arrivee")
    list_select_related = ("user", "foyer")
    search_fields = ("user__email", "foyer__nom")
    ordering = ("date_arrivee",)
