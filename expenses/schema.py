import logging

import graphene
from graphene_django import DjangoObjectType
from graphql import GraphQLError

from config.graphql_utils import save_via_serializer
from groups.models import Group
from notifications.tasks import notify_members
from settlements.services import invalidate_balances_cache

from .models import Expense, ExpenseSplit
from .serializers import ExpenseSerializer

logger = logging.getLogger(__name__)


class ExpenseSplitType(DjangoObjectType):
    class Meta:
        model = ExpenseSplit
        fields = ("id", "user", "share_amount")


class ExpenseType(DjangoObjectType):
    class Meta:
        model = Expense
        fields = ("id", "group", "description", "amount", "paid_by", "created_at", "splits")


class ExpenseSplitInput(graphene.InputObjectType):
    user = graphene.ID(required=True)
    share_amount = graphene.Decimal(required=True)


class Query(graphene.ObjectType):
    expenses = graphene.List(ExpenseType, group_id=graphene.ID())
    expense = graphene.Field(ExpenseType, id=graphene.ID(required=True))

    def resolve_expenses(root, info, group_id=None):
        qs = Expense.objects.filter(group__members=info.context.user).distinct()
        if group_id:
            qs = qs.filter(group_id=group_id)
        return qs

    def resolve_expense(root, info, id):
        return Expense.objects.filter(group__members=info.context.user, id=id).distinct().first()


def _require_membership(user, group_id):
    if not Group.objects.filter(id=group_id, members=user).exists():
        raise GraphQLError("Not a member of that group.")


def _notify(expense, actor, message):
    try:
        notify_members.delay(expense.group_id, actor.id, message)
    except Exception:
        # ponytail: notifications are best-effort; a down broker shouldn't
        # fail the expense write.
        logger.warning("notify_members enqueue failed", exc_info=True)


class CreateExpense(graphene.Mutation):
    class Arguments:
        group = graphene.ID(required=True)
        description = graphene.String(required=True)
        amount = graphene.Decimal(required=True)
        paid_by = graphene.ID(required=True)
        splits = graphene.List(ExpenseSplitInput)

    expense = graphene.Field(ExpenseType)

    def mutate(root, info, group, description, amount, paid_by, splits=None):
        _require_membership(info.context.user, group)
        data = {"group": group, "description": description, "amount": amount, "paid_by": paid_by}
        if splits is not None:
            data["splits"] = [{"user": s.user, "share_amount": s.share_amount} for s in splits]
        expense = save_via_serializer(ExpenseSerializer, data, context={"request": info.context})
        invalidate_balances_cache(expense.group_id)
        _notify(expense, info.context.user, f"{info.context.user.username} added '{expense.description}' (${expense.amount})")
        return CreateExpense(expense=expense)


class DeleteExpense(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(root, info, id):
        expense = Expense.objects.filter(group__members=info.context.user, id=id).distinct().first()
        if expense is None:
            raise GraphQLError("Expense not found.")
        group_id = expense.group_id
        expense.delete()
        invalidate_balances_cache(group_id)
        return DeleteExpense(ok=True)


class Mutation(graphene.ObjectType):
    create_expense = CreateExpense.Field()
    delete_expense = DeleteExpense.Field()
