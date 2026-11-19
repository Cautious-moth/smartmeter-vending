
import hashlib
import hmac
import json
import time

import uuid
from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from django.test import SimpleTestCase, TestCase, override_settings

from customers.models import Customer
from meters.models import Meter
from vending.models import VendingPurchase
from vending.services import initiate_simulated_payment

from transactions.models import Transaction, PaymentWebhookEvent
from transactions.services import process_payment_webhook

from .webhook_security import verify_webhook_signature


@override_settings(PAYMENT_WEBHOOK_SECRET="test-webhook-secret")
class WebhookSignatureTests(SimpleTestCase):

    def setUp(self):
        self.raw_body = (
            b'{"event_id":"evt_001","type":"payment.succeeded"}'
        )
        self.timestamp = str(int(time.time()))

    def create_signature(self, body=None, timestamp=None):
        body = body if body is not None else self.raw_body
        timestamp = timestamp or self.timestamp

        signed_payload = (
            timestamp.encode("utf-8") + b"." + body
        )

        return hmac.new(
            b"test-webhook-secret",
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

    def test_valid_signature_is_accepted(self):
        signature = self.create_signature()

        result = verify_webhook_signature(
            self.raw_body,
            self.timestamp,
            signature,
        )

        self.assertTrue(result)

    def test_invalid_signature_is_rejected(self):
        result = verify_webhook_signature(
            self.raw_body,
            self.timestamp,
            "invalid-signature",
        )

        self.assertFalse(result)

    def test_tampered_payload_is_rejected(self):
        signature = self.create_signature()

        tampered_body = (
            b'{"event_id":"evt_001","type":"payment.failed"}'
        )

        result = verify_webhook_signature(
            tampered_body,
            self.timestamp,
            signature,
        )

        self.assertFalse(result)

    def test_missing_signature_is_rejected(self):
        result = verify_webhook_signature(
            self.raw_body,
            self.timestamp,
            None,
        )

        self.assertFalse(result)

    def test_expired_timestamp_is_rejected(self):
        old_timestamp = str(int(time.time()) - 600)
        signature = self.create_signature(
            timestamp=old_timestamp,
        )

        result = verify_webhook_signature(
            self.raw_body,
            old_timestamp,
            signature,
        )

        self.assertFalse(result)

    def test_sha256_signature_prefix_is_supported(self):
        signature = "sha256=" + self.create_signature()

        result = verify_webhook_signature(
            self.raw_body,
            self.timestamp,
            signature,
        )

        self.assertTrue(result)

class PaymentWebhookProcessingTests(TestCase):

    def setUp(self):
        self.customer = Customer.objects.create(
            full_name="Webhook Test Customer",
            email="webhook@example.com",
            phone_number="0821234567",
        )

        self.meter = Meter.objects.create(
            customer=self.customer,
            meter_number="WEBHOOK-METER-001",
            meter_type=Meter.MeterType.PREPAID,
            status=Meter.Status.ACTIVE,
        )

        self.purchase = VendingPurchase.objects.create(
            meter=self.meter,
            amount=Decimal("150.00"),
        )

        self.purchase, self.payment, _ = initiate_simulated_payment(
            self.purchase.id,
            "webhook-test-idempotency-key",
        )

    def build_payload(self, event_type="payment.succeeded", **overrides):
        payload = {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "data": {
                "transaction_reference": str(self.payment.reference),
                "amount": "150.00",
            },
        }

        payload.update(overrides)
        return payload

    def test_successful_webhook_updates_payment_and_purchase(self):
        event, created = process_payment_webhook(
            self.build_payload()
        )

        self.payment.refresh_from_db()
        self.purchase.refresh_from_db()

        self.assertTrue(created)
        self.assertEqual(self.payment.status, Transaction.Status.SUCCESS)
        self.assertEqual(self.purchase.status, VendingPurchase.Status.PAID)
        self.assertEqual(event.status, PaymentWebhookEvent.Status.PROCESSED)

    def test_failed_webhook_updates_payment_and_purchase(self):
        event, created = process_payment_webhook(
            self.build_payload("payment.failed")
        )

        self.payment.refresh_from_db()
        self.purchase.refresh_from_db()

        self.assertTrue(created)
        self.assertEqual(self.payment.status, Transaction.Status.FAILED)
        self.assertEqual(self.purchase.status, VendingPurchase.Status.FAILED)

    def test_duplicate_webhook_is_not_processed_twice(self):
        payload = self.build_payload()

        first_event, first_created = process_payment_webhook(payload)
        second_event, second_created = process_payment_webhook(payload)

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first_event.id, second_event.id)
        self.assertEqual(PaymentWebhookEvent.objects.count(), 1)

    def test_reused_event_id_with_different_payload_is_rejected(self):
        payload = self.build_payload()
        process_payment_webhook(payload)

        modified_payload = {
            **payload,
            "data": {
                **payload["data"],
                "amount": "200.00",
            },
        }

        with self.assertRaises(Exception):
            process_payment_webhook(modified_payload)

    def test_incorrect_amount_is_rejected(self):
        payload = self.build_payload()
        payload["data"]["amount"] = "200.00"

        with self.assertRaises(Exception):
            process_payment_webhook(payload)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Transaction.Status.PENDING)

    def test_unknown_transaction_is_rejected(self):
        payload = self.build_payload()
        payload["data"]["transaction_reference"] = str(uuid.uuid4())

        with self.assertRaises(Exception):
            process_payment_webhook(payload)

    def test_non_pending_transaction_cannot_be_processed_again(self):
        payload = self.build_payload()
        process_payment_webhook(payload)

        second_payload = self.build_payload("payment.failed")

        with self.assertRaises(Exception):
            process_payment_webhook(second_payload)

@override_settings(PAYMENT_WEBHOOK_SECRET="test-webhook-secret")
class PaymentWebhookAPITests(APITestCase):

    def setUp(self):
        self.customer = Customer.objects.create(
            full_name="API Webhook Customer",
            email="api-webhook@example.com",
            phone_number="0821234568",
        )

        self.meter = Meter.objects.create(
            customer=self.customer,
            meter_number="API-WEBHOOK-METER-001",
            meter_type=Meter.MeterType.PREPAID,
            status=Meter.Status.ACTIVE,
        )

        self.purchase = VendingPurchase.objects.create(
            meter=self.meter,
            amount=Decimal("150.00"),
        )

        self.purchase, self.payment, _ = initiate_simulated_payment(
            self.purchase.id,
            "api-webhook-idempotency-key",
        )

        self.url = "/api/webhooks/payment/"

    def build_payload(self):
        return {
            "id": str(uuid.uuid4()),
            "type": "payment.succeeded",
            "data": {
                "transaction_reference": str(self.payment.reference),
                "amount": "150.00",
            },
        }

    def build_headers(self, raw_body, timestamp=None):
        timestamp = timestamp or str(int(time.time()))

        signed_payload = timestamp.encode() + b"." + raw_body

        signature = hmac.new(
            b"test-webhook-secret",
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        return {
            "HTTP_X_WEBHOOK_TIMESTAMP": timestamp,
            "HTTP_X_WEBHOOK_SIGNATURE": signature,
        }

    def test_valid_webhook_returns_200(self):
        raw_body = json.dumps(self.build_payload()).encode()

        response = self.client.generic(
            "POST",
            self.url,
            raw_body,
            content_type="application/json",
            **self.build_headers(raw_body),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_signature_returns_401(self):
        raw_body = json.dumps(self.build_payload()).encode()

        response = self.client.generic(
            "POST",
            self.url,
            raw_body,
            content_type="application/json",
            HTTP_X_WEBHOOK_TIMESTAMP=str(int(time.time())),
            HTTP_X_WEBHOOK_SIGNATURE="invalid-signature",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_tampered_payload_returns_401(self):
        original_body = json.dumps(self.build_payload()).encode()
        headers = self.build_headers(original_body)

        tampered_body = original_body.replace(b"150.00", b"200.00")

        response = self.client.generic(
            "POST",
            self.url,
            tampered_body,
            content_type="application/json",
            **headers,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_expired_timestamp_returns_401(self):
        raw_body = json.dumps(self.build_payload()).encode()
        old_timestamp = str(int(time.time()) - 600)

        response = self.client.generic(
            "POST",
            self.url,
            raw_body,
            content_type="application/json",
            **self.build_headers(raw_body, old_timestamp),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_duplicate_webhook_returns_200_without_duplicate_event(self):
        raw_body = json.dumps(self.build_payload()).encode()
        headers = self.build_headers(raw_body)

        first_response = self.client.generic(
            "POST",
            self.url,
            raw_body,
            content_type="application/json",
            **headers,
        )

        second_response = self.client.generic(
            "POST",
            self.url,
            raw_body,
            content_type="application/json",
            **headers,
        )

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(PaymentWebhookEvent.objects.count(), 1)