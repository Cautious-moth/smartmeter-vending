from rest_framework import serializers
from .models import Meter


class MeterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meter
        fields = [
            "id",
            "customer",
            "meter_number",
            "meter_type",
            "status",
            "installation_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
