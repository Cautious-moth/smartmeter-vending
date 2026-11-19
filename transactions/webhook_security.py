
import hashlib
import hmac
import time

from django.conf import settings


def verify_webhook_signature(
    raw_body,
    timestamp,
    signature,
    tolerance_seconds=300,
):
    """
    Verify an HMAC-SHA256 webhook signature.

    Signed message format:
        timestamp.raw_request_body

    Returns False for missing, malformed, invalid,
    or expired signatures.
    """

    secret = settings.PAYMENT_WEBHOOK_SECRET

    if not secret or not timestamp or not signature:
        return False

    try:
        timestamp_value = int(timestamp)
    except (TypeError, ValueError):
        return False

    current_time = int(time.time())

    if abs(current_time - timestamp_value) > tolerance_seconds:
        return False

    signed_payload = (
        timestamp.encode("utf-8")
        + b"."
        + raw_body
    )

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()

    supplied_signature = signature

    if supplied_signature.startswith("sha256="):
        supplied_signature = supplied_signature[7:]

    return hmac.compare_digest(
        expected_signature,
        supplied_signature,
    )
