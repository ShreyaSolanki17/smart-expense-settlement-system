from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Group


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class GroupSerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, read_only=True)
    member_ids = serializers.PrimaryKeyRelatedField(
        source="members", queryset=User.objects.all(), many=True, write_only=True, required=False
    )

    class Meta:
        model = Group
        fields = ["id", "name", "members", "member_ids", "created_at"]
        read_only_fields = ["created_at"]
