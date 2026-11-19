from django.contrib import admin
from .models import Meter


@admin.register(Meter)
class MeterAdmin(admin.ModelAdmin):
    list_display = (
        "meter_number",
        "customer",
        "meter_type",
        "status",
        "installation_date",
    )

    search_fields = (
        "meter_number",
        "customer__full_name",
    )

    list_filter = ("meter_type", "status")