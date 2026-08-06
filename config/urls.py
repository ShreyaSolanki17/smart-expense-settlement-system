from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from expenses.views import ExpenseViewSet
from groups.views import GroupViewSet, demo_login, me, register, search_users
from notifications.views import NotificationViewSet
from settlements.views import SettlementViewSet

router = DefaultRouter()
router.register("groups", GroupViewSet, basename="group")
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("settlements", SettlementViewSet, basename="settlement")
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/auth/register/", register),
    path("api/auth/login/", obtain_auth_token),
    path("api/auth/demo/", demo_login),
    path("api/auth/me/", me),
    path("api/users/", search_users),
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),
]
