import json

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .webhook_security import verify_webhook_signature
from .services import process_payment_webhook
from rest_framework.exceptions import ValidationError

from django.shortcuts import render

class PaymentWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        raw_body = request._request.body

        timestamp = request.headers.get("X-Webhook-Timestamp")
        signature = request.headers.get("X-Webhook-Signature")

        if not verify_webhook_signature(
            raw_body,
            timestamp,
            signature,
        ):
            return Response(
                {"error": "Invalid webhook signature."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            payload = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response(
                {"error": "Invalid JSON payload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            event, created = process_payment_webhook(payload)
        except ValidationError as exc:
            return Response(
                {"error": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": (
                    "Webhook processed."
                    if created
                    else "Webhook already processed."
                ),
                "event_id": event.provider_event_id,
                "event_status": event.status,
            },
            status=status.HTTP_200_OK,
        )
