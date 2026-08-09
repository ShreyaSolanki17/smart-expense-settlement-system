import graphene

import expenses.schema
import groups.schema
import notifications.schema
import settlements.schema
from groups.schema import UserType


class Query(
    groups.schema.Query,
    expenses.schema.Query,
    settlements.schema.Query,
    notifications.schema.Query,
    graphene.ObjectType,
):
    me = graphene.Field(UserType)

    def resolve_me(root, info):
        return info.context.user


class Mutation(
    groups.schema.Mutation,
    expenses.schema.Mutation,
    settlements.schema.Mutation,
    notifications.schema.Mutation,
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
