from django.contrib.auth.models import User
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from settlements.services import compute_balances, simplify_debts

from .models import Group
from .serializers import GroupSerializer, UserSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    if not username or not password:
        return Response({"detail": "username and password are required."}, status=400)
    if User.objects.filter(username=username).exists():
        return Response({"detail": "username already taken."}, status=400)

    user = User.objects.create_user(username=username, password=password)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": UserSerializer(user).data}, status=201)


DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo1234"


@api_view(["POST"])
@permission_classes([AllowAny])
def demo_login(request):
    user, created = User.objects.get_or_create(username=DEMO_USERNAME)
    if created:
        user.set_password(DEMO_PASSWORD)
        user.save()
        _seed_demo_data(user)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": UserSerializer(user).data})


def _seed_demo_data(user):
    from decimal import Decimal

    from expenses.models import Expense, ExpenseSplit

    bob, _ = User.objects.get_or_create(username="demo_bob")
    bob.set_unusable_password()
    bob.save()
    carol, _ = User.objects.get_or_create(username="demo_carol")
    carol.set_unusable_password()
    carol.save()

    group = Group.objects.create(name="Weekend Trip")
    group.members.add(user, bob, carol)

    dinner = Expense.objects.create(
        group=group, description="Dinner", amount=Decimal("60.00"), paid_by=user
    )
    ExpenseSplit.objects.bulk_create(
        [
            ExpenseSplit(expense=dinner, user=user, share_amount=Decimal("20.00")),
            ExpenseSplit(expense=dinner, user=bob, share_amount=Decimal("20.00")),
            ExpenseSplit(expense=dinner, user=carol, share_amount=Decimal("20.00")),
        ]
    )

    gas = Expense.objects.create(
        group=group, description="Gas", amount=Decimal("30.00"), paid_by=bob
    )
    ExpenseSplit.objects.bulk_create(
        [
            ExpenseSplit(expense=gas, user=user, share_amount=Decimal("10.00")),
            ExpenseSplit(expense=gas, user=bob, share_amount=Decimal("10.00")),
            ExpenseSplit(expense=gas, user=carol, share_amount=Decimal("10.00")),
        ]
    )


@api_view(["GET"])
def me(request):
    return Response(UserSerializer(request.user).data)


@api_view(["GET"])
def search_users(request):
    query = request.query_params.get("q", "").strip()
    users = User.objects.exclude(id=request.user.id)
    if query:
        users = users.filter(username__icontains=query)
    return Response(UserSerializer(users[:10], many=True).data)


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
