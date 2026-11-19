
from django.shortcuts import get_object_or_404

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import VendingPurchase
from .serializers import VendingPurchaseSerializer
from .services import process_simulated_payment


class VendingPurchaseViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):

    queryset = VendingPurchase.objects.select_related(
        "meter",
        "meter__customer",
    ).all()

    serializer_class = VendingPurchaseSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=["post"])
    def simulate_payment(self, request, pk=None):

        simulate_failure = request.data.get(
            "simulate_failure",
            False,
        )

        if not isinstance(simulate_failure, bool):
            return Response(
                {"error": "simulate_failure must be a boolean."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        purchase = get_object_or_404(
            self.get_queryset(),
            pk=pk,
        )

        purchase, payment, created = process_simulated_payment(
            purchase_id=purchase.id,
            idempotency_key=request.headers.get("Idempotency-Key"),
            simulate_failure=simulate_failure,
        )

        if payment.status == "SUCCESS":
            message = "Simulated payment successful."
        else:
            message = "Simulated payment failed."

        if not created:
            message = "Existing payment returned (idempotent replay)."

        return Response(
            {
                "message": message,
                "idempotent_replay": not created,
                "purchase": {
                    "id": purchase.id,
                    "reference": str(purchase.reference),
                    "amount": str(purchase.amount),
                    "status": purchase.status,
                },
                "payment": {
                    "id": payment.id,
                    "reference": str(payment.reference),
                    "amount": str(payment.amount),
                    "status": payment.status,
                    "payment_method": payment.payment_method,
                },
            },
            status=status.HTTP_200_OK,
        )
