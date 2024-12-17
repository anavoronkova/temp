from rest_framework import generics, permissions
from .serializers import UserSerializer
from django.contrib.auth import get_user_model

class UserProfileView(generics.RetrieveAPIView):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
