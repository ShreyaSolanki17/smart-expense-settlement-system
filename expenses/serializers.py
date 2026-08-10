from decimal import Decimal

from rest_framework import serializers

from groups.permissions import require_group_member

from .models import Expense, ExpenseSplit


class ExpenseSplitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseSplit
        fields = ["id", "user", "share_amount"]


class ExpenseSerializer(serializers.ModelSerializer):
    splits = ExpenseSplitSerializer(many=True, required=False)

    class Meta:
        model = Expense
        fields = ["id", "group", "description", "amount", "paid_by", "created_at", "splits"]
        read_only_fields = ["created_at"]

    def validate(self, attrs):
        group = attrs.get("group") or getattr(self.instance, "group", None)
        splits = attrs.get("splits")
        amount = attrs.get("amount", getattr(self.instance, "amount", None))

        request = self.context.get("request")
        if request is not None:
            require_group_member(request.user, group)

        if splits:
            member_ids = set(group.members.values_list("id", flat=True))
            for split in splits:
                if split["user"].id not in member_ids:
                    raise serializers.ValidationError(
                        f"{split['user']} is not a member of {group}."
                    )
            total = sum((s["share_amount"] for s in splits), Decimal("0"))
            if total != amount:
                raise serializers.ValidationError(
                    f"Split shares ({total}) must add up to the expense amount ({amount})."
                )
        return attrs

    def create(self, validated_data):
        splits_data = validated_data.pop("splits", None)
        expense = Expense.objects.create(**validated_data)
        if splits_data:
            ExpenseSplit.objects.bulk_create(
                ExpenseSplit(expense=expense, **split) for split in splits_data
            )
        else:
            self._create_equal_splits(expense)
        return expense

    def update(self, instance, validated_data):
        splits_data = validated_data.pop("splits", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if splits_data is not None:
            instance.splits.all().delete()
            ExpenseSplit.objects.bulk_create(
                ExpenseSplit(expense=instance, **split) for split in splits_data
            )
        return instance

    @staticmethod
    def _create_equal_splits(expense):
        """No splits given: divide the amount equally, handing the leftover
        cents (from integer division) to the first members so shares always
        add back up to the exact expense amount."""
        members = list(expense.group.members.all())
        if not members:
            return
        cents = int(expense.amount * 100)
        base, remainder = divmod(cents, len(members))
        splits = [
            ExpenseSplit(
                expense=expense,
                user=member,
                share_amount=Decimal(base + (1 if i < remainder else 0)) / 100,
            )
            for i, member in enumerate(members)
        ]
        ExpenseSplit.objects.bulk_create(splits)
