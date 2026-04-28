"""Middlewares custom du projet."""
from __future__ import annotations

from django.http import HttpResponse
from django_ratelimit.exceptions import Ratelimited


class RatelimitedTo429Middleware:
    """Convertit les `Ratelimited` (PermissionDenied) en réponse HTTP 429.

    Sans ce middleware, le décorateur ``@ratelimit(block=True)`` propage une
    `PermissionDenied`, transformée par Django en 403 — ce qui ment au client
    sur la nature du blocage. On rend ici un 429 explicite.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, Ratelimited):
            return HttpResponse(
                "Trop de requêtes. Veuillez réessayer dans quelques minutes.",
                status=429,
                content_type="text/plain; charset=utf-8",
            )
        return None
