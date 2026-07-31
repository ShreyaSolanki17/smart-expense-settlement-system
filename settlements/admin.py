from django.contrib import admin

from .models import Settlement


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ("group", "from_user", "to_user", "amount", "settled_at")
    list_filter = ("group",)
