import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from expenses.models import Expense
from groups.models import Group


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
