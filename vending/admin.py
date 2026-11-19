from django.contrib import admin
from .models import VendingPurchase


@admin.register(VendingPurchase)
class VendingPurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "meter",
        "amount",
        "status",
        "created_at",
    )
    search_fields = ("reference", "meter__meter_number")
    list_filter = ("status",)