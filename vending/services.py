from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import VendingPurchase
from transactions.models import Transaction


@transaction.atomic
def simulate_payment(purchase_id):
    """
    Process a simulated successful payment.

    The purchase and payment transaction are updated
    within a single database transaction.
    """

    purchase = (
        VendingPurchase.objects
        .select_for_update()
        .get(id=purchase_id)
    )

    if purchase.status != VendingPurchase.Status.PENDING:
        raise ValidationError(
            "This purchase has already been processed."
        )

    payment = Transaction.objects.create(
        purchase=purchase,
        amount=purchase.amount,
        payment_method=Transaction.PaymentMethod.SIMULATED,
        status=Transaction.Status.SUCCESS,
    )

    purchase.status = VendingPurchase.Status.PAID
    purchase.save(update_fields=["status", "updated_at"])

    return purchase, payment