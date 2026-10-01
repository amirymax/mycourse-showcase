from django.db import models


class ThrottleBlock(models.Model):
    """DRF keeps rate-limit state in the cache, which is opaque to admins. This
    table records *who got blocked* so an operator can see and clear it."""

    scope = models.CharField(max_length=50)
    ident = models.CharField(max_length=64, help_text="IP or user id - same key DRF uses")
    blocked_until = models.DateTimeField()
    hit_count = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["scope", "ident"], name="uniq_throttle_scope_ident")]
        indexes = [models.Index(fields=["blocked_until"])]
