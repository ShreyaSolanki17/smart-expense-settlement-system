import graphene
from django.contrib.auth.models import User
from graphene_django import DjangoObjectType
from graphql import GraphQLError

from config.graphql_utils import save_via_serializer
from settlements.services import get_group_balances

from .models import Group
from .serializers import GroupSerializer


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ("id", "username", "email")


class GroupType(DjangoObjectType):
    class Meta:
        model = Group
        fields = ("id", "name", "members", "created_at", "expenses", "settlements")


class BalanceType(graphene.ObjectType):
    from_user = graphene.Int()
    to_user = graphene.Int()
    amount = graphene.String()


class Query(graphene.ObjectType):
    groups = graphene.List(GroupType)
    group = graphene.Field(GroupType, id=graphene.ID(required=True))
    balances = graphene.List(BalanceType, group_id=graphene.ID(required=True))

    def resolve_groups(root, info):
        return Group.objects.filter(members=info.context.user).distinct()

    def resolve_group(root, info, id):
        return Group.objects.filter(members=info.context.user, id=id).distinct().first()

    def resolve_balances(root, info, group_id):
        group = Group.objects.filter(members=info.context.user, id=group_id).distinct().first()
        if group is None:
            return []
        return [BalanceType(**t) for t in get_group_balances(group)]


class CreateGroup(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)

    group = graphene.Field(GroupType)

    def mutate(root, info, name):
        group = save_via_serializer(GroupSerializer, {"name": name}, context={"request": info.context})
        group.members.add(info.context.user)
        return CreateGroup(group=group)


class AddGroupMember(graphene.Mutation):
    """ponytail: member-add only, no remove mutation yet — nothing in the
    REST API needs it either; add DeleteGroupMember alongside it when it does.
    """

    class Arguments:
        group_id = graphene.ID(required=True)
        user_id = graphene.ID(required=True)

    group = graphene.Field(GroupType)

    def mutate(root, info, group_id, user_id):
        group = Group.objects.filter(members=info.context.user, id=group_id).distinct().first()
        if group is None:
            raise GraphQLError("Group not found.")
        group.members.add(user_id)
        return AddGroupMember(group=group)


class Mutation(graphene.ObjectType):
    create_group = CreateGroup.Field()
    add_group_member = AddGroupMember.Field()
