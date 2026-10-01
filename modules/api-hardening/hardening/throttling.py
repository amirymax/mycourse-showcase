import logging
from datetime import timedelta

from django.utils import timezone
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

logger = logging.getLogger(__name__)


class TrackedThrottleMixin:
    """Adds observability to DRF throttling without changing how limits work:
    every block is also recorded in the DB (``ThrottleBlock``)."""

    def allow_request(self, request, view):
        self._tracked_request = request
        return super().allow_request(request, view)

    def throttle_failure(self):
        self._record_block()
        return super().throttle_failure()

    def _record_block(self):
        from .models import ThrottleBlock

        try:
            ident = self.get_ident(self._tracked_request)
            blocked_until = timezone.now() + timedelta(seconds=self.wait() or 0)
            obj, created = ThrottleBlock.objects.get_or_create(
                scope=self.scope, ident=ident, defaults={"blocked_until": blocked_until},
            )
            if not created:
                obj.blocked_until = blocked_until
                obj.hit_count += 1
                obj.save(update_fields=["blocked_until", "hit_count", "updated_at"])
        except Exception:  # never let logging break request handling
            logger.exception("Failed to record throttle block")


class TrackedAnonRateThrottle(TrackedThrottleMixin, AnonRateThrottle):
    pass


class TrackedUserRateThrottle(TrackedThrottleMixin, UserRateThrottle):
    pass


# One scope per abuse surface, rates live in settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].
class LoginRateThrottle(TrackedThrottleMixin, AnonRateThrottle):
    scope = "login"


class PasswordResetRateThrottle(TrackedThrottleMixin, AnonRateThrottle):
    """Main enumeration/abuse vector -> conservative limit."""
    scope = "password_reset"


class ExpensiveCallRateThrottle(TrackedThrottleMixin, AnonRateThrottle):
    """Endpoints that cost real money per call (e.g. LLM grading) get their own,
    stricter bucket, independent of any per-feature attempt limits."""
    scope = "expensive_call"
