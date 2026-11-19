from rest_framework.routers import DefaultRouter
from .views import MeterViewSet

router = DefaultRouter()
router.register("meters", MeterViewSet, basename="meter")

urlpatterns = router.urls
