from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from expenses.views import ExpenseViewSet
from groups.views import GroupViewSet, demo_login, me, register, search_users
from settlements.views import SettlementViewSet

router = DefaultRouter()
router.register("groups", GroupViewSet, basename="group")
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("settlements", SettlementViewSet, basename="settlement")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/register/", register),
    path("api/auth/login/", obtain_auth_token),
    path("api/auth/demo/", demo_login),
    path("api/auth/me/", me),
    path("api/users/", search_users),
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),
]
