
from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import VendingPurchase
from transactions.models import Transaction


@transaction.atomic
def process_simulated_payment(
    purchase_id,
    idempotency_key,
    simulate_failure=False,
):
    """
    Process a simulated payment safely.

    Repeated requests with the same idempotency key return
    the original transaction instead of creating duplicates.
    """

    if not idempotency_key or not idempotency_key.strip():
        raise ValidationError("An idempotency key is required.")

    idempotency_key = idempotency_key.strip()

    if len(idempotency_key) > 128:
        raise ValidationError(
            "The idempotency key cannot exceed 128 characters."
        )

    purchase = (
        VendingPurchase.objects
        .select_for_update()
        .get(id=purchase_id)
    )

    existing_payment = Transaction.objects.filter(
        idempotency_key=idempotency_key
    ).first()

    if existing_payment:
        if existing_payment.purchase_id != purchase.id:
            raise ValidationError(
                "This idempotency key has already been used "
                "for another purchase."
            )

        return purchase, existing_payment, False

    if purchase.status != VendingPurchase.Status.PENDING:
        raise ValidationError(
            "This purchase has already been processed."
        )

    payment_status = (
        Transaction.Status.FAILED
        if simulate_failure
        else Transaction.Status.SUCCESS
    )

    purchase_status = (
        VendingPurchase.Status.FAILED
        if simulate_failure
        else VendingPurchase.Status.PAID
    )

    payment = Transaction.objects.create(
        purchase=purchase,
        amount=purchase.amount,
        payment_method=Transaction.PaymentMethod.SIMULATED,
        status=payment_status,
        idempotency_key=idempotency_key,
    )

    purchase.status = purchase_status
    purchase.save(update_fields=["status", "updated_at"])

    return purchase, payment, True
