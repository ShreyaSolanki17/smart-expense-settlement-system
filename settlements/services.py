"""Debt simplification: reduce a group's net balances to a minimal-ish set
of settling transactions using a greedy heap-based max-creditor/max-debtor
match. This is not guaranteed globally optimal (minimizing transaction count
exactly is NP-hard) but is the standard practical approach and never needs
more than n-1 transactions for n people with non-zero balance.
"""

import heapq
import itertools
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, Hashable, List, NamedTuple

TWO_PLACES = Decimal("0.01")


class Transaction(NamedTuple):
    from_user: Hashable
    to_user: Hashable
    amount: Decimal


def simplify_debts(balances: Dict[Hashable, Decimal]) -> List[Transaction]:
    """balances: user -> net balance (positive = owed money, negative = owes money).

    Returns a list of Transaction(from_user, to_user, amount) that settles
    every balance to zero.
    """
    counter = itertools.count()
    creditors: List[tuple] = []
    debtors: List[tuple] = []
    total = Decimal("0")

    for user, raw_balance in balances.items():
        amount = Decimal(raw_balance).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        total += amount
        if amount > 0:
            heapq.heappush(creditors, (-amount, next(counter), user))
        elif amount < 0:
            heapq.heappush(debtors, (amount, next(counter), user))

    if total != 0:
        raise ValueError(f"Balances must net to zero, got {total}")

    transactions: List[Transaction] = []

    while creditors and debtors:
        neg_credit, _, creditor = heapq.heappop(creditors)
        debt, _, debtor = heapq.heappop(debtors)

        credit = -neg_credit
        owed = -debt
        settled = min(credit, owed)

        transactions.append(Transaction(from_user=debtor, to_user=creditor, amount=settled))

        remaining_credit = credit - settled
        remaining_debt = owed - settled

        if remaining_credit > 0:
            heapq.heappush(creditors, (-remaining_credit, next(counter), creditor))
        if remaining_debt > 0:
            heapq.heappush(debtors, (-remaining_debt, next(counter), debtor))

    return transactions
