from decimal import Decimal

from rest_framework import serializers

from groups.permissions import require_group_member

from .models import Settlement
from .services import compute_balances


class SettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settlement
        fields = ["id", "group", "from_user", "to_user", "amount", "settled_at"]
        read_only_fields = ["settled_at"]

    def validate(self, attrs):
        from_user = attrs.get("from_user", getattr(self.instance, "from_user", None))
        to_user = attrs.get("to_user", getattr(self.instance, "to_user", None))
        group = attrs.get("group", getattr(self.instance, "group", None))
        amount = attrs.get("amount", getattr(self.instance, "amount", None))

        request = self.context.get("request")
        if request is not None:
            require_group_member(request.user, group)

        if from_user == to_user:
            raise serializers.ValidationError("from_user and to_user must be different.")

        balances = compute_balances(group)
        if self.instance is not None:
            # Undo this settlement's own prior contribution so editing it
            # validates against the balance as it would be without it.
            balances[self.instance.from_user_id] = (
                balances.get(self.instance.from_user_id, Decimal("0")) - self.instance.amount
            )
            balances[self.instance.to_user_id] = (
                balances.get(self.instance.to_user_id, Decimal("0")) + self.instance.amount
            )

        owed = -balances.get(from_user.id, Decimal("0"))
        if amount > owed:
            raise serializers.ValidationError(
                f"{from_user} only owes {max(owed, Decimal('0'))} in {group}, cannot settle {amount}."
            )

        return attrs
