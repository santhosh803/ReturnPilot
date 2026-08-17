from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet,
    CustomerViewSet,
    OrderViewSet,
    ReturnRequestViewSet,
    ReturnPolicyViewSet,
    RefundLedgerViewSet,
    WebhookView,
    AnalyticsView,
)

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"customers", CustomerViewSet, basename="customer")
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"returns", ReturnRequestViewSet, basename="returnrequest")
router.register(r"policies", ReturnPolicyViewSet, basename="returnpolicy")
router.register(r"refunds", RefundLedgerViewSet, basename="refundledger")

urlpatterns = [
    path("", include(router.urls)),
    path("webhooks/shopify/", WebhookView.as_view(), name="shopify-webhook"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
]
