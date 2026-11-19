from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "purchase",
        "amount",
        "payment_method",
        "status",
        "created_at",
    )
    search_fields = ("reference", "purchase__reference")
    list_filter = ("status", "payment_method")