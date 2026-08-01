from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from groups.models import Group

from .models import Expense


class ExpenseViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="x")
        self.other = User.objects.create_user("bob", password="x")
        self.outsider = User.objects.create_user("eve", password="x")
        self.group = Group.objects.create(name="trip")
        self.group.members.add(self.user, self.other)
        self.client.force_authenticate(self.user)

    def test_create_without_splits_divides_equally(self):
        response = self.client.post(
            "/api/expenses/",
            {"group": self.group.id, "description": "dinner", "amount": "30.00", "paid_by": self.user.id},
        )

        self.assertEqual(response.status_code, 201)
        expense = Expense.objects.get(id=response.data["id"])
        amounts = sorted(expense.splits.values_list("share_amount", flat=True))
        self.assertEqual(amounts, [Decimal("15.00"), Decimal("15.00")])

    def test_create_rejects_splits_not_summing_to_amount(self):
        response = self.client.post(
            "/api/expenses/",
            {
                "group": self.group.id,
                "description": "dinner",
                "amount": "30.00",
                "paid_by": self.user.id,
                "splits": [
                    {"user": self.user.id, "share_amount": "10.00"},
                    {"user": self.other.id, "share_amount": "10.00"},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_create_rejects_split_for_non_member(self):
        response = self.client.post(
            "/api/expenses/",
            {
                "group": self.group.id,
                "description": "dinner",
                "amount": "10.00",
                "paid_by": self.user.id,
                "splits": [{"user": self.outsider.id, "share_amount": "10.00"}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_list_only_returns_expenses_in_users_groups(self):
        visible = Expense.objects.create(
            group=self.group, description="dinner", amount=Decimal("10.00"), paid_by=self.user
        )
        other_group = Group.objects.create(name="other")
        other_group.members.add(self.outsider)
        Expense.objects.create(
            group=other_group, description="hidden", amount=Decimal("5.00"), paid_by=self.outsider
        )

        response = self.client.get("/api/expenses/")

        ids = {e["id"] for e in response.data["results"]}
        self.assertEqual(ids, {visible.id})
