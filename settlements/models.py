from django.conf import settings
from django.db import models

from groups.models import Group


class Settlement(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="settlements")
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="settlements_paid"
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="settlements_received"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    settled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name="settlement_amount_positive"),
            models.CheckConstraint(
                check=~models.Q(from_user=models.F("to_user")), name="settlement_from_ne_to_user"
            ),
        ]
        ordering = ["-settled_at"]

    def __str__(self):
        return f"{self.from_user} paid {self.to_user} {self.amount}"
