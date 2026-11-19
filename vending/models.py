import uuid

from django.db import models


class VendingPurchase(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        TOKEN_ISSUED = "TOKEN_ISSUED", "Token Issued"
        FAILED = "FAILED", "Failed"

    reference = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    meter = models.ForeignKey(
        "meters.Meter",
        on_delete=models.PROTECT,
        related_name="vending_purchases"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    token_code = models.CharField(
        max_length=32,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} - R{self.amount}"