from rest_framework import serializers

from .models import Settlement


class SettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settlement
        fields = ["id", "group", "from_user", "to_user", "amount", "settled_at"]
        read_only_fields = ["settled_at"]

    def validate(self, attrs):
        from_user = attrs.get("from_user", getattr(self.instance, "from_user", None))
        to_user = attrs.get("to_user", getattr(self.instance, "to_user", None))
        if from_user == to_user:
            raise serializers.ValidationError("from_user and to_user must be different.")
        return attrs
