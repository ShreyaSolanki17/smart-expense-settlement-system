from django.contrib.auth.models import User
from django.test import TestCase

from groups.models import Group

from .models import Notification
from .tasks import notify_members


class NotifyMembersTests(TestCase):
    def test_notifies_every_member_except_actor(self):
        actor = User.objects.create_user("alice")
        bob = User.objects.create_user("bob")
        carol = User.objects.create_user("carol")
        group = Group.objects.create(name="Trip")
        group.members.add(actor, bob, carol)

        # Calling the task directly (not .delay) runs it synchronously,
        # no broker needed.
        notify_members(group.id, actor.id, "alice added Dinner")

        recipients = set(Notification.objects.values_list("user_id", flat=True))
        self.assertEqual(recipients, {bob.id, carol.id})
