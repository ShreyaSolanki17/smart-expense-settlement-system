from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from .models import Settlement
from .serializers import SettlementSerializer


class SettlementViewSet(viewsets.ModelViewSet):
    serializer_class = SettlementSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["group", "from_user", "to_user"]

    def get_queryset(self):
        return Settlement.objects.filter(group__members=self.request.user).distinct()
