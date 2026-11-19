
from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APITestCase

from customers.models import Customer
from meters.models import Meter
from transactions.models import Transaction
from .models import VendingPurchase


class SimulatedPaymentAPITests(APITestCase):

    def setUp(self):
        self.customer = Customer.objects.create(
            full_name="Test Customer",
            email="test.customer@example.com",
            phone_number="0710000000",
            address="Test Address",
        )

        self.meter = Meter.objects.create(
            customer=self.customer,
            meter_number="TEST-METER-001",
            meter_type=Meter.MeterType.PREPAID,
            status=Meter.Status.ACTIVE,
        )

        self.purchase = self.create_purchase()

        self.url = reverse(
            "vending-purchase-simulate-payment",
            kwargs={"pk": self.purchase.pk},
        )

    def create_purchase(self):
        return VendingPurchase.objects.create(
            meter=self.meter,
            amount=Decimal("250.00"),
        )

    def make_payment_request(
        self,
        purchase,
        key,
        simulate_failure=False,
    ):
        url = reverse(
            "vending-purchase-simulate-payment",
            kwargs={"pk": purchase.pk},
        )

        return self.client.post(
            url,
            {"simulate_failure": simulate_failure},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )

    def test_successful_payment(self):
        response = self.make_payment_request(
            self.purchase,
            "payment-success-001",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["purchase"]["status"],
            VendingPurchase.Status.PAID,
        )
        self.assertEqual(
            response.data["payment"]["status"],
            Transaction.Status.SUCCESS,
        )
        self.assertFalse(response.data["idempotent_replay"])

        self.assertEqual(Transaction.objects.count(), 1)

    def test_failed_payment(self):
        response = self.make_payment_request(
            self.purchase,
            "payment-failure-001",
            simulate_failure=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["purchase"]["status"],
            VendingPurchase.Status.FAILED,
        )
        self.assertEqual(
            response.data["payment"]["status"],
            Transaction.Status.FAILED,
        )

        self.assertEqual(Transaction.objects.count(), 1)

    def test_duplicate_request_returns_original_payment(self):
        first_response = self.make_payment_request(
            self.purchase,
            "payment-duplicate-001",
        )

        second_response = self.make_payment_request(
            self.purchase,
            "payment-duplicate-001",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)

        self.assertEqual(
            first_response.data["payment"]["id"],
            second_response.data["payment"]["id"],
        )

        self.assertFalse(
            first_response.data["idempotent_replay"]
        )
        self.assertTrue(
            second_response.data["idempotent_replay"]
        )

        self.assertEqual(Transaction.objects.count(), 1)

    def test_idempotency_key_cannot_be_reused_for_another_purchase(self):
        another_purchase = self.create_purchase()

        first_response = self.make_payment_request(
            self.purchase,
            "shared-payment-key-001",
        )

        second_response = self.make_payment_request(
            another_purchase,
            "shared-payment-key-001",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 400)

        self.assertEqual(Transaction.objects.count(), 1)

    def test_already_processed_purchase_rejects_new_key(self):
        first_response = self.make_payment_request(
            self.purchase,
            "payment-first-attempt-001",
        )

        second_response = self.make_payment_request(
            self.purchase,
            "payment-second-attempt-001",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 400)

        self.assertEqual(Transaction.objects.count(), 1)

    def test_missing_idempotency_key_is_rejected(self):
        response = self.client.post(
            self.url,
            {"simulate_failure": False},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_invalid_simulate_failure_value_is_rejected(self):
        response = self.client.post(
            self.url,
            {"simulate_failure": "yes"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="payment-invalid-001",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Transaction.objects.count(), 0)
