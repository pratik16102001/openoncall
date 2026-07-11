from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import LoginView, TeamViewSet
from apps.escalation.views import EscalationPolicyViewSet
from apps.incidents.views import IncidentViewSet
from apps.notifications.views import PushSubscriptionView
from apps.schedules.views import ScheduleViewSet
from apps.services.views import ServiceViewSet

app_name = "api"

router = DefaultRouter()
router.register("teams", TeamViewSet, basename="team")
router.register("schedules", ScheduleViewSet, basename="schedule")
router.register("escalation-policies", EscalationPolicyViewSet, basename="escalation-policy")
router.register("services", ServiceViewSet, basename="service")
router.register("incidents", IncidentViewSet, basename="incident")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("push-subscriptions/", PushSubscriptionView.as_view(), name="push-subscriptions"),
] + router.urls
