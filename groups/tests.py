from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from expenses.models import Expense, ExpenseSplit

from .models import Group


class GroupViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="x")
        self.other = User.objects.create_user("bob", password="x")
        self.client.force_authenticate(self.user)

    def test_create_group_adds_creator_as_member(self):
        response = self.client.post("/api/groups/", {"name": "trip"})
        self.assertEqual(response.status_code, 201)
        group = Group.objects.get(id=response.data["id"])
        self.assertIn(self.user, group.members.all())

    def test_list_only_returns_groups_user_belongs_to(self):
        mine = Group.objects.create(name="mine")
        mine.members.add(self.user)
        theirs = Group.objects.create(name="theirs")
        theirs.members.add(self.other)

        response = self.client.get("/api/groups/")

        ids = {g["id"] for g in response.data["results"]}
        self.assertEqual(ids, {mine.id})

    def test_balances_action_returns_suggested_transactions(self):
        group = Group.objects.create(name="trip")
        group.members.add(self.user, self.other)
        expense = Expense.objects.create(
            group=group, description="dinner", amount=Decimal("30.00"), paid_by=self.user
        )
        ExpenseSplit.objects.bulk_create(
            [
                ExpenseSplit(expense=expense, user=self.user, share_amount=Decimal("15.00")),
                ExpenseSplit(expense=expense, user=self.other, share_amount=Decimal("15.00")),
            ]
        )

        response = self.client.get(f"/api/groups/{group.id}/balances/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            [{"from_user": self.other.id, "to_user": self.user.id, "amount": "15.00"}],
        )

    def test_balances_action_forbidden_for_non_member(self):
        group = Group.objects.create(name="trip")
        group.members.add(self.other)

        response = self.client.get(f"/api/groups/{group.id}/balances/")

        self.assertEqual(response.status_code, 404)
