from rest_framework.routers import DefaultRouter

from .views import VendingPurchaseViewSet


router = DefaultRouter()

router.register(
    "vending/purchases",
    VendingPurchaseViewSet,
    basename="vending-purchase",
)

urlpatterns = router.urls
