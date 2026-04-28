"""Endpoint de healthcheck — utilisé par Traefik et le pipeline CD.

Doit rester très léger : ping DB + cache, pas d'auth, pas de session.
"""
from __future__ import annotations

from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, JsonResponse


def health(_request: HttpRequest) -> JsonResponse:
    """Renvoie 200 si DB et cache répondent, 503 sinon."""
    statut = {"db": "ok", "cache": "ok"}
    code = 200

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:  # noqa: BLE001 — on veut renvoyer un 503 clair
        statut["db"] = f"erreur: {exc.__class__.__name__}"
        code = 503

    try:
        cache.set("__health__", "ok", timeout=5)
        if cache.get("__health__") != "ok":
            statut["cache"] = "lecture inattendue"
            code = 503
    except Exception as exc:  # noqa: BLE001
        statut["cache"] = f"erreur: {exc.__class__.__name__}"
        code = 503

    return JsonResponse(statut, status=code)
