from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import LoginView, TeamViewSet
from apps.notifications.views import PushSubscriptionView

app_name = "api"

router = DefaultRouter()
router.register("teams", TeamViewSet, basename="team")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("push-subscriptions/", PushSubscriptionView.as_view(), name="push-subscriptions"),
] + router.urls
