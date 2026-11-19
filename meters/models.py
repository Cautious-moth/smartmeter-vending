
from django.db import models


class Meter(models.Model):

    class MeterType(models.TextChoices):
        PREPAID = "PREPAID", "Prepaid"
        SMART_PREPAID = "SMART_PREPAID", "Smart Prepaid"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        MAINTENANCE = "MAINTENANCE", "Maintenance"

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="meters"
    )

    meter_number = models.CharField(
        max_length=32,
        unique=True
    )

    meter_type = models.CharField(
        max_length=20,
        choices=MeterType.choices,
        default=MeterType.PREPAID
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    installation_date = models.DateField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["meter_number"]

    def __str__(self):
        return self.meter_number
