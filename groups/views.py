from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from settlements.services import compute_balances, simplify_debts

from .models import Group
from .serializers import GroupSerializer


class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializer

    def get_queryset(self):
        return Group.objects.filter(members=self.request.user).distinct()

    def perform_create(self, serializer):
        group = serializer.save()
        group.members.add(self.request.user)

    @action(detail=True, methods=["get"])
    def balances(self, request, pk=None):
        group = self.get_object()
        transactions = simplify_debts(compute_balances(group))
        return Response(
            [
                {"from_user": t.from_user, "to_user": t.to_user, "amount": str(t.amount)}
                for t in transactions
            ]
        )
