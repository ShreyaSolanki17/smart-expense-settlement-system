import graphene
from graphene_django import DjangoObjectType
from graphql import GraphQLError

from .models import Notification


class NotificationType(DjangoObjectType):
    class Meta:
        model = Notification
        fields = ("id", "message", "created_at", "read")


class Query(graphene.ObjectType):
    notifications = graphene.List(NotificationType)

    def resolve_notifications(root, info):
        return Notification.objects.filter(user=info.context.user)


class MarkNotificationRead(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    notification = graphene.Field(NotificationType)

    def mutate(root, info, id):
        notification = Notification.objects.filter(user=info.context.user, id=id).first()
        if notification is None:
            raise GraphQLError("Notification not found.")
        notification.read = True
        notification.save(update_fields=["read"])
        return MarkNotificationRead(notification=notification)


class Mutation(graphene.ObjectType):
    mark_notification_read = MarkNotificationRead.Field()
