from django.contrib import admin

from .models import Foyer, Invitation, MembreFoyer


@admin.register(Foyer)
class FoyerAdmin(admin.ModelAdmin):
    list_display = ("nom", "cree_par", "date_creation")
    list_select_related = ("cree_par",)
    search_fields = ("nom", "cree_par__email")
    ordering = ("-date_creation",)


@admin.register(MembreFoyer)
class MembreFoyerAdmin(admin.ModelAdmin):
    list_display = ("user", "foyer", "date_arrivee")
    list_select_related = ("user", "foyer")
    search_fields = ("user__email", "foyer__nom")
    ordering = ("date_arrivee",)


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "prenom", "foyer", "statut", "date_creation", "date_expiration")
    list_select_related = ("foyer", "cree_par")
    list_filter = ("statut",)
    search_fields = ("email", "prenom", "foyer__nom")
    readonly_fields = ("token", "date_creation")
    ordering = ("-date_creation",)
