from django.conf import settings
from django.db import models

from groups.models import Group


class Expense(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="expenses")
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expenses_paid"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name="expense_amount_positive"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.description} ({self.amount})"


class ExpenseSplit(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="splits")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expense_splits"
    )
    share_amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["expense", "user"], name="unique_split_per_user_per_expense"),
            models.CheckConstraint(check=models.Q(share_amount__gte=0), name="expense_split_share_non_negative"),
        ]

    def __str__(self):
        return f"{self.user} owes {self.share_amount} for {self.expense}"
