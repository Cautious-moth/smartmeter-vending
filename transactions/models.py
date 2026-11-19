import uuid

from django.db import models


class Transaction(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    class PaymentMethod(models.TextChoices):
        SIMULATED = "SIMULATED", "Simulated Payment"

    reference = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    idempotency_key = models.CharField(
    max_length=128,
    unique=True,
    null=True,
    blank=True,
    )

    purchase = models.ForeignKey(
        "vending.VendingPurchase",
        on_delete=models.PROTECT,
        related_name="transactions"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.SIMULATED
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} - {self.status}"