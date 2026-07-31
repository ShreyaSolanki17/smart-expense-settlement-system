from django.contrib import admin

from .models import Group


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "member_count", "created_at")
    search_fields = ("name",)
    filter_horizontal = ("members",)

    @admin.display(description="Members")
    def member_count(self, obj):
        return obj.members.count()
