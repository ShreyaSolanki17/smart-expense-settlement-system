from django.contrib import admin

from .models import Expense, ExpenseSplit


class ExpenseSplitInline(admin.TabularInline):
    model = ExpenseSplit
    extra = 1


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("description", "group", "paid_by", "amount", "created_at")
    list_filter = ("group",)
    search_fields = ("description",)
    inlines = [ExpenseSplitInline]
