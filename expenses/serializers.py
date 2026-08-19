from rest_framework import serializers

from .models import User, Group, Expense, ExpenseParticipant

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name', 'members', 'created_at']

class ExpenseParticipantSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    amount_owed = serializers.DecimalField(max_digits=10, decimal_places=2)

class ExpenseCreateSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=255)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    paid_by_id = serializers.IntegerField()
    group_id = serializers.IntegerField(required=False, allow_null=True)
    splits = ExpenseParticipantSerializer(many=True)

    def validate(self, data):
        """
        Object-level validation: Enforces that sum(splits) == total_amount.
        If mathematical integrity fails, DRF returns HTTP 400 Bad Request.
        """
        total_amount = data['amount']
        splits = data.get('splits', [])
        split_sum = sum(item['amount_owed'] for item in splits)

        if split_sum != total_amount:
            raise serializers.ValidationError(
                f"Sum of participant splits ({split_sum}) must equal total amount ({total_amount})."
            )
        return data