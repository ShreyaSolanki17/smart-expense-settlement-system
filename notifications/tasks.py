from celery import shared_task


@shared_task
def notify_members(group_id, actor_id, message):
    from groups.models import Group

    from .models import Notification

    group = Group.objects.get(id=group_id)
    recipients = group.members.exclude(id=actor_id)
    Notification.objects.bulk_create(
        Notification(user=user, message=message) for user in recipients
    )
