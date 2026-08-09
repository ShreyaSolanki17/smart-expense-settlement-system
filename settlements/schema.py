import logging

import graphene
from graphene_django import DjangoObjectType
from graphql import GraphQLError

from config.graphql_utils import save_via_serializer
from groups.models import Group
from notifications.tasks import notify_members

from .models import Settlement
from .serializers import SettlementSerializer
from .services import invalidate_balances_cache

logger = logging.getLogger(__name__)


class SettlementType(DjangoObjectType):
    class Meta:
        model = Settlement
        fields = ("id", "group", "from_user", "to_user", "amount", "settled_at")


class Query(graphene.ObjectType):
    settlements = graphene.List(SettlementType, group_id=graphene.ID())

    def resolve_settlements(root, info, group_id=None):
        qs = Settlement.objects.filter(group__members=info.context.user).distinct()
        if group_id:
            qs = qs.filter(group_id=group_id)
        return qs


class CreateSettlement(graphene.Mutation):
    class Arguments:
        group = graphene.ID(required=True)
        from_user = graphene.ID(required=True)
        to_user = graphene.ID(required=True)
        amount = graphene.Decimal(required=True)

    settlement = graphene.Field(SettlementType)

    def mutate(root, info, group, from_user, to_user, amount):
        if not Group.objects.filter(id=group, members=info.context.user).exists():
            raise GraphQLError("Not a member of that group.")
        data = {"group": group, "from_user": from_user, "to_user": to_user, "amount": amount}
        settlement = save_via_serializer(SettlementSerializer, data, context={"request": info.context})
        invalidate_balances_cache(settlement.group_id)
        message = f"{settlement.from_user.username} paid {settlement.to_user.username} ${settlement.amount}"
        try:
            notify_members.delay(settlement.group_id, info.context.user.id, message)
        except Exception:
            # ponytail: notifications are best-effort; a down broker
            # shouldn't fail the settlement write.
            logger.warning("notify_members enqueue failed", exc_info=True)
        return CreateSettlement(settlement=settlement)


class Mutation(graphene.ObjectType):
    create_settlement = CreateSettlement.Field()
