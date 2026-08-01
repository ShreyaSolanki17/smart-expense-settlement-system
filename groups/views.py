from rest_framework import viewsets

from .models import Group
from .serializers import GroupSerializer


class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializer

    def get_queryset(self):
        return Group.objects.filter(members=self.request.user).distinct()

    def perform_create(self, serializer):
        group = serializer.save()
        group.members.add(self.request.user)
