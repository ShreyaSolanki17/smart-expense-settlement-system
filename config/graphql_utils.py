from graphql import GraphQLError


def save_via_serializer(serializer_class, data, instance=None, context=None):
    """Run an existing DRF serializer inside a GraphQL mutation, so create/
    update validation lives in one place (the serializer) instead of being
    re-implemented per mutation. Raises GraphQLError with the serializer's
    own validation messages on failure.
    """
    serializer = serializer_class(instance=instance, data=data, partial=instance is not None, context=context or {})
    if not serializer.is_valid():
        raise GraphQLError(str(serializer.errors))
    return serializer.save()
