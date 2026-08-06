import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from notifications.tasks import notify_members
from settlements.services import invalidate_balances_cache

from .models import Expense
from .serializers import ExpenseSerializer

logger = logging.getLogger(__name__)


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["group", "paid_by"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Expense.objects.none()
        return Expense.objects.filter(group__members=self.request.user).distinct()

    def perform_create(self, serializer):
        expense = serializer.save()
        invalidate_balances_cache(expense.group_id)
        self._notify(expense, f"{self.request.user.username} added '{expense.description}' (${expense.amount})")

    def perform_update(self, serializer):
        expense = serializer.save()
        invalidate_balances_cache(expense.group_id)

    def perform_destroy(self, instance):
        group_id = instance.group_id
        instance.delete()
        invalidate_balances_cache(group_id)

    def _notify(self, expense, message):
        try:
            notify_members.delay(expense.group_id, self.request.user.id, message)
        except Exception:
            # ponytail: notifications are best-effort; a down broker
            # shouldn't fail the expense write.
            logger.warning("notify_members enqueue failed", exc_info=True)
