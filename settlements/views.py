import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from notifications.tasks import notify_members

from .models import Settlement
from .serializers import SettlementSerializer
from .services import invalidate_balances_cache

logger = logging.getLogger(__name__)


class SettlementViewSet(viewsets.ModelViewSet):
    serializer_class = SettlementSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["group", "from_user", "to_user"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Settlement.objects.none()
        return Settlement.objects.filter(group__members=self.request.user).distinct()

    def perform_create(self, serializer):
        settlement = serializer.save()
        invalidate_balances_cache(settlement.group_id)
        message = f"{settlement.from_user.username} paid {settlement.to_user.username} ${settlement.amount}"
        try:
            notify_members.delay(settlement.group_id, self.request.user.id, message)
        except Exception:
            # ponytail: notifications are best-effort; a down broker
            # shouldn't fail the settlement write.
            logger.warning("notify_members enqueue failed", exc_info=True)

    def perform_update(self, serializer):
        settlement = serializer.save()
        invalidate_balances_cache(settlement.group_id)

    def perform_destroy(self, instance):
        group_id = instance.group_id
        instance.delete()
        invalidate_balances_cache(group_id)
