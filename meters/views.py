from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models import Meter
from .serializers import MeterSerializer


class MeterViewSet(viewsets.ModelViewSet):
    queryset = Meter.objects.select_related("customer").all()
    serializer_class = MeterSerializer
    permission_classes = [AllowAny]
