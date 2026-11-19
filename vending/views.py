from django.shortcuts import get_object_or_404

from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import VendingPurchase
from .serializers import VendingPurchaseSerializer
from .services import simulate_payment


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

        purchase = get_object_or_404(
            self.get_queryset(),
            pk=pk,
        )

        purchase, payment = simulate_payment(purchase.id)

        return Response(
            {
                "message": "Simulated payment successful.",
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