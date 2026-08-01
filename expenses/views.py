from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from .models import Expense
from .serializers import ExpenseSerializer


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["group", "paid_by"]

    def get_queryset(self):
        return Expense.objects.filter(group__members=self.request.user).distinct()
