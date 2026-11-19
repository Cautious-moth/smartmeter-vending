
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from vending.models import VendingPurchase
from .models import Transaction, PaymentWebhookEvent


@transaction.atomic
def process_payment_webhook(payload):
    """
    Process a verified simulated payment webhook atomically.

    Expected payload:
    {
        "id": "evt_001",
        "type": "payment.succeeded",
        "data": {
            "transaction_reference": "transaction-uuid",
            "amount": "150.00"
        }
    }
    """

    if not isinstance(payload, dict):
        raise ValidationError("Webhook payload must be a JSON object.")

    event_id = payload.get("id")
    event_type = payload.get("type")
    data = payload.get("data")

    if not event_id or not isinstance(event_id, str):
        raise ValidationError("A valid event ID is required.")

    if event_type not in PaymentWebhookEvent.EventType.values:
        raise ValidationError("Unsupported payment event type.")

    if not isinstance(data, dict):
        raise ValidationError("Webhook data must be an object.")

    transaction_reference = data.get("transaction_reference")
    amount_value = data.get("amount")

    if not transaction_reference or amount_value is None:
        raise ValidationError(
            "Transaction reference and amount are required."
        )

    try:
        webhook_amount = Decimal(str(amount_value))
    except (InvalidOperation, ValueError):
        raise ValidationError("Invalid payment amount.")

    if not webhook_amount.is_finite() or webhook_amount <= 0:
        raise ValidationError("Payment amount must be positive and finite.")

    # Return an existing event when the provider retries the same payload.
    existing_event = PaymentWebhookEvent.objects.filter(
        provider_event_id=event_id
    ).first()

    if existing_event:
        if existing_event.payload != payload:
            raise ValidationError(
                "This event ID has already been used with a different payload."
            )

        if existing_event.status == PaymentWebhookEvent.Status.PROCESSED:
            return existing_event, False

        raise ValidationError("This webhook event was not successfully processed.")

    # Lock the transaction to prevent concurrent payment updates.
    try:
        payment = (
            Transaction.objects
            .select_for_update()
            .get(reference=transaction_reference)
        )
    except (Transaction.DoesNotExist, ValueError):
        raise ValidationError("Transaction not found.")

    purchase = (
        VendingPurchase.objects
        .select_for_update()
        .get(id=payment.purchase_id)
    )

    if payment.status != Transaction.Status.PENDING:
        raise ValidationError("Transaction is not pending.")

    if purchase.status != VendingPurchase.Status.PENDING:
        raise ValidationError("Purchase is not pending.")

    if webhook_amount != payment.amount:
        raise ValidationError("Webhook amount does not match the transaction.")

    # Record the event inside the same database transaction.
    try:
        with transaction.atomic():
            event = PaymentWebhookEvent.objects.create(
                provider_event_id=event_id,
                event_type=event_type,
                transaction=payment,
                payload=payload,
                signature_verified=True,
            )
    except IntegrityError:
        # A concurrent request may have inserted this event.
        existing_event = PaymentWebhookEvent.objects.filter(
            provider_event_id=event_id
        ).first()

        if existing_event is None:
            raise

        if existing_event.payload != payload:
            raise ValidationError(
                "This event ID has already been used with a different payload."
            )

        if existing_event.status == PaymentWebhookEvent.Status.PROCESSED:
            return existing_event, False

        raise ValidationError("This webhook event was not successfully processed.")

    if event_type == PaymentWebhookEvent.EventType.PAYMENT_SUCCEEDED:
        payment.status = Transaction.Status.SUCCESS
        purchase.status = VendingPurchase.Status.PAID

    else:
        payment.status = Transaction.Status.FAILED
        purchase.status = VendingPurchase.Status.FAILED

    payment.save(update_fields=["status"])

    purchase.save(update_fields=["status", "updated_at"])

    event.status = PaymentWebhookEvent.Status.PROCESSED
    event.processed_at = timezone.now()
    event.save(update_fields=["status", "processed_at"])

    return event, True
