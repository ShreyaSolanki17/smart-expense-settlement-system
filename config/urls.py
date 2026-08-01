from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from expenses.views import ExpenseViewSet
from groups.views import GroupViewSet
from settlements.views import SettlementViewSet

router = DefaultRouter()
router.register("groups", GroupViewSet, basename="group")
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("settlements", SettlementViewSet, basename="settlement")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),
]
