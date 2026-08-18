from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from .views import (
    ProductViewSet,
    CustomerViewSet,
    OrderViewSet,
    ReturnRequestViewSet,
    ReturnPolicyViewSet,
    RefundLedgerViewSet,
    WebhookView,
    AnalyticsView,
    AgentChatView,
    AgentApproveView,
    AgentSessionViewSet,
)

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"customers", CustomerViewSet, basename="customer")
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"returns", ReturnRequestViewSet, basename="returnrequest")
router.register(r"policies", ReturnPolicyViewSet, basename="returnpolicy")
router.register(r"refunds", RefundLedgerViewSet, basename="refundledger")
router.register(r"agent/sessions", AgentSessionViewSet, basename="agent-session")

urlpatterns = [
    path("", include(router.urls)),
    # POST {username, password} → {token}. Always open so clients can authenticate
    # even when REQUIRE_API_AUTH gates the rest of the API.
    path("auth/token/", obtain_auth_token, name="auth-token"),
    path("webhooks/shopify/", WebhookView.as_view(), name="shopify-webhook"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
    path("agent/chat/", AgentChatView.as_view(), name="agent-chat"),
    path("agent/approve/", AgentApproveView.as_view(), name="agent-approve"),
]
