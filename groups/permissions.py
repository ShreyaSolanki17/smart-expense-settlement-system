from rest_framework import serializers


def require_group_member(user, group):
    """Raise a DRF ValidationError unless `user` belongs to `group`.

    IsAuthenticated (the API's default permission) only proves who's
    calling, not that they belong to the group a write is scoped to. This
    is the shared gate for any group-scoped write (expenses, settlements)
    — called from the serializers' validate() so both REST and GraphQL
    (which reuses the same serializers via save_via_serializer) get it for
    free instead of each mutation re-implementing its own check.
    """
    if not group.members.filter(id=user.id).exists():
        raise serializers.ValidationError(f"You are not a member of {group}.")
