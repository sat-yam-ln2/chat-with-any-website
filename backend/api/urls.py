from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WebsiteViewSet

router = DefaultRouter()
router.register(r'websites', WebsiteViewSet)

urlpatterns = [
    path('', include(router.urls)),
]