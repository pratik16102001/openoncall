from django.urls import path

from .views import AlertWebhookView

app_name = "alerts"

urlpatterns = [
    path(
        "alertmanager/<str:integration_key>/",
        AlertWebhookView.as_view(source="alertmanager"),
        name="webhook-alertmanager",
    ),
    path(
        "datadog/<str:integration_key>/",
        AlertWebhookView.as_view(source="datadog"),
        name="webhook-datadog",
    ),
    path(
        "cloudwatch/<str:integration_key>/",
        AlertWebhookView.as_view(source="cloudwatch"),
        name="webhook-cloudwatch",
    ),
    path(
        "sentry/<str:integration_key>/",
        AlertWebhookView.as_view(source="sentry"),
        name="webhook-sentry",
    ),
    path(
        "generic/<str:integration_key>/",
        AlertWebhookView.as_view(source="generic"),
        name="webhook-generic",
    ),
]
