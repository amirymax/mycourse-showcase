import secrets

from django.conf import settings
from rest_framework.permissions import BasePermission


class HasServiceAPIKey(BasePermission):
    """Server-to-server calls authenticate with a static key in ``X-API-Key``.

    * Constant-time comparison (``secrets.compare_digest``) -> no timing oracle.
    * Fail closed: if the key is not configured, the endpoint is unavailable to
      everyone (rather than open to everyone).
    """

    message = "Invalid or missing API key."

    def has_permission(self, request, view):
        expected = getattr(settings, "SERVICE_API_KEY", "")
        if not expected:
            return False
        provided = request.headers.get("X-API-Key", "")
        return secrets.compare_digest(provided.encode(), expected.encode())
