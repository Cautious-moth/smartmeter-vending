from rest_framework import serializers

from .models import VendingPurchase
from meters.models import Meter


class VendingPurchaseSerializer(serializers.ModelSerializer):

    class Meta:
        model = VendingPurchase
        fields = [
            "id",
            "reference",
            "meter",
            "amount",
            "status",
            "token_code",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "reference",
            "status",
            "token_code",
            "created_at",
            "updated_at",
        ]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Purchase amount must be greater than zero."
            )

        return value

    def validate_meter(self, value):
        if value.status != Meter.Status.ACTIVE:
            raise serializers.ValidationError(
                "Cannot create a purchase for an inactive meter."
            )

        return value