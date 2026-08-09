import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from expenses.models import Expense, ExpenseSplit
from groups.models import Group
from settlements.models import Settlement


class GraphQLSmokeTests(TestCase):
    """One end-to-end check per concern the GraphQL layer adds on top of the
    REST API: auth is required, queries are scoped to the caller's groups,
    and a mutation reuses the same serializer validation REST uses.
    """

    def setUp(self):
        self.user = User.objects.create_user("alice", password="x")
        self.other = User.objects.create_user("bob", password="x")
        self.group = Group.objects.create(name="trip")
        self.group.members.add(self.user, self.other)

    def query(self, query, variables=None):
        return self.client.post(
            "/graphql/",
            data=json.dumps({"query": query, "variables": variables or {}}),
            content_type="application/json",
        )

    def test_requires_authentication(self):
        response = self.query("{ groups { id } }")
        self.assertEqual(response.status_code, 401)

    def test_groups_scoped_to_caller(self):
        Group.objects.create(name="not mine")
        self.client.force_login(self.user)

        response = self.query("{ groups { name } }")

        self.assertEqual(response.status_code, 200)
        names = [g["name"] for g in response.json()["data"]["groups"]]
        self.assertEqual(names, ["trip"])

    def test_create_expense_mutation_reuses_serializer_validation(self):
        self.client.force_login(self.user)
        mutation = """
        mutation($group: ID!, $paidBy: ID!) {
          createExpense(group: $group, description: "dinner", amount: "30.00", paidBy: $paidBy) {
            expense { id amount splits { shareAmount } }
          }
        }
        """

        response = self.query(mutation, {"group": self.group.id, "paidBy": self.user.id})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertNotIn("errors", body)
        expense_id = body["data"]["createExpense"]["expense"]["id"]
        amounts = sorted(Expense.objects.get(id=expense_id).splits.values_list("share_amount", flat=True))
        self.assertEqual(amounts, [Decimal("15.00"), Decimal("15.00")])

    def test_create_expense_rejects_non_member_group(self):
        outsider_group = Group.objects.create(name="not mine")
        outsider_group.members.add(self.other)
        self.client.force_login(self.user)
        mutation = """
        mutation($group: ID!, $paidBy: ID!) {
          createExpense(group: $group, description: "x", amount: "10.00", paidBy: $paidBy) {
            expense { id }
          }
        }
        """

        response = self.query(mutation, {"group": outsider_group.id, "paidBy": self.user.id})

        self.assertIn("errors", response.json())

    def test_group_detail_query_shape_matches_frontend(self):
        """Guards the exact query frontend/src/graphql.js sends — same shape
        used to need two REST calls (listExpenses + getBalances)."""
        expense = Expense.objects.create(
            group=self.group, description="dinner", amount=Decimal("20.00"), paid_by=self.user
        )
        ExpenseSplit.objects.create(expense=expense, user=self.user, share_amount=Decimal("10.00"))
        ExpenseSplit.objects.create(expense=expense, user=self.other, share_amount=Decimal("10.00"))
        self.client.force_login(self.user)
        query = """
        query GroupDetail($groupId: ID!) {
          expenses(groupId: $groupId) { id description amount paidBy { username } }
          balances(groupId: $groupId) { fromUser toUser amount }
        }
        """

        response = self.query(query, {"groupId": self.group.id})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertNotIn("errors", body)
        self.assertEqual(body["data"]["expenses"][0]["paidBy"]["username"], "alice")

    def test_create_settlement_mutation_matches_frontend_shape(self):
        """Guards the exact mutation frontend/src/graphql.js sends for
        AddExpense's settle button (was api.createSettlement over REST)."""
        expense = Expense.objects.create(
            group=self.group, description="dinner", amount=Decimal("20.00"), paid_by=self.user
        )
        ExpenseSplit.objects.create(expense=expense, user=self.user, share_amount=Decimal("0.00"))
        ExpenseSplit.objects.create(expense=expense, user=self.other, share_amount=Decimal("20.00"))
        self.client.force_login(self.user)
        mutation = """
        mutation CreateSettlement($group: ID!, $fromUser: ID!, $toUser: ID!, $amount: Decimal!) {
          createSettlement(group: $group, fromUser: $fromUser, toUser: $toUser, amount: $amount) {
            settlement { id }
          }
        }
        """

        response = self.query(
            mutation,
            {"group": self.group.id, "fromUser": self.other.id, "toUser": self.user.id, "amount": "20.00"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertNotIn("errors", body)
        settlement_id = body["data"]["createSettlement"]["settlement"]["id"]
        self.assertTrue(Settlement.objects.filter(id=settlement_id, amount=Decimal("20.00")).exists())
