from decimal import Decimal
from unittest import TestCase

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from groups.models import Group
from settlements.services import simplify_debts

from .models import Settlement


class SimplifyDebtsTests(TestCase):
    def assert_settles_to_zero(self, balances, transactions):
        net = dict.fromkeys(balances, Decimal("0"))
        for txn in transactions:
            self.assertGreater(txn.amount, 0)
            net[txn.from_user] -= txn.amount
            net[txn.to_user] += txn.amount
        for user, balance in balances.items():
            self.assertEqual(net[user], Decimal(balance).quantize(Decimal("0.01")))

    def test_empty_balances(self):
        self.assertEqual(simplify_debts({}), [])

    def test_all_zero_balances(self):
        self.assertEqual(simplify_debts({"a": Decimal("0"), "b": Decimal("0")}), [])

    def test_two_users_simple_debt(self):
        balances = {"a": Decimal("-10.00"), "b": Decimal("10.00")}
        transactions = simplify_debts(balances)
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0], ("a", "b", Decimal("10.00")))

    def test_reduces_three_way_cycle_to_two_transactions(self):
        # naive pairwise settlement here would take 3 transactions;
        # the simplified result should only need 2.
        balances = {
            "a": Decimal("-30.00"),
            "b": Decimal("10.00"),
            "c": Decimal("20.00"),
        }
        transactions = simplify_debts(balances)
        self.assertEqual(len(transactions), 2)
        self.assert_settles_to_zero(balances, transactions)

    def test_never_needs_more_than_n_minus_1_transactions(self):
        balances = {
            "a": Decimal("-50.00"),
            "b": Decimal("-25.00"),
            "c": Decimal("30.00"),
            "d": Decimal("45.00"),
        }
        transactions = simplify_debts(balances)
        non_zero_users = {u for u, b in balances.items() if b != 0}
        self.assertLessEqual(len(transactions), len(non_zero_users) - 1)
        self.assert_settles_to_zero(balances, transactions)

    def test_rounding_to_two_decimal_places(self):
        balances = {"a": Decimal("-10.005"), "b": Decimal("10.005")}
        transactions = simplify_debts(balances)
        self.assertEqual(transactions[0].amount, Decimal("10.01"))

    def test_raises_when_balances_do_not_net_to_zero(self):
        with self.assertRaises(ValueError):
            simplify_debts({"a": Decimal("-10.00"), "b": Decimal("5.00")})

    def test_partial_settlement_leaves_correct_remainder(self):
        # one big creditor split across two debtors of different sizes
        balances = {
            "a": Decimal("-5.00"),
            "b": Decimal("-15.00"),
            "c": Decimal("20.00"),
        }
        transactions = simplify_debts(balances)
        self.assertEqual(len(transactions), 2)
        self.assert_settles_to_zero(balances, transactions)


class SettlementViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="x")
        self.other = User.objects.create_user("bob", password="x")
        self.group = Group.objects.create(name="trip")
        self.group.members.add(self.user, self.other)
        self.client.force_authenticate(self.user)

    def test_create_settlement(self):
        response = self.client.post(
            "/api/settlements/",
            {
                "group": self.group.id,
                "from_user": self.other.id,
                "to_user": self.user.id,
                "amount": "10.00",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Settlement.objects.count(), 1)

    def test_rejects_settlement_from_user_to_self(self):
        response = self.client.post(
            "/api/settlements/",
            {
                "group": self.group.id,
                "from_user": self.user.id,
                "to_user": self.user.id,
                "amount": "10.00",
            },
        )

        self.assertEqual(response.status_code, 400)
