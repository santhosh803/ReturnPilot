import hmac
import hashlib
import json
import logging
import os
from decimal import Decimal
from django.utils import timezone
from django.db.models import Count, Sum
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import (
    Product,
    Customer,
    Order,
    OrderItem,
    ReturnPolicy,
    ReturnRequest,
    RefundLedger,
    AgentSession,
)
from .serializers import (
    ProductSerializer,
    CustomerSerializer,
    OrderSerializer,
    ReturnPolicySerializer,
    ReturnRequestSerializer,
    RefundLedgerSerializer,
    AgentSessionSerializer,
)

logger = logging.getLogger(__name__)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category"]
    search_fields = ["sku", "name", "description"]
    ordering_fields = ["price", "created_at", "name", "inventory_count"]
    ordering = ["-created_at"]


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "email"]
    ordering_fields = ["return_count", "lifetime_value", "risk_score", "created_at"]
    ordering = ["-created_at"]


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Order.objects.select_related("customer").prefetch_related("items__product").all()
    serializer_class = OrderSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "customer"]
    search_fields = ["order_id", "customer__name", "customer__email"]
    ordering_fields = ["order_date", "total", "created_at"]
    ordering = ["-order_date"]


class ReturnRequestViewSet(viewsets.ModelViewSet):
    queryset = (
        ReturnRequest.objects.select_related("order", "order__customer", "refund")
        .prefetch_related("items__product")
        .all()
    )
    serializer_class = ReturnRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "reason_classified", "order"]
    search_fields = [
        "return_id",
        "order__order_id",
        "order__customer__email",
        "order__customer__name",
        "reason_text",
    ]
    ordering_fields = ["created_at", "refund_amount", "status"]
    ordering = ["-created_at"]


class ReturnPolicyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReturnPolicy.objects.all()
    serializer_class = ReturnPolicySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "exchange_allowed"]
    search_fields = ["category", "conditions"]
    ordering = ["category"]


class RefundLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RefundLedger.objects.select_related("return_request").all()
    serializer_class = RefundLedgerSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["decision", "method"]
    search_fields = ["return_request__return_id", "decided_by", "reason"]
    ordering_fields = ["amount", "decided_at"]
    ordering = ["-decided_at"]


class WebhookView(APIView):
    """
    Mock Shopify / eCommerce order webhook endpoint.
    Accepts POST requests with order events like `orders/fulfilled` or `orders/create`.
    Validates shared secret if configured via SHOPIFY_WEBHOOK_SECRET env var.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        webhook_secret = os.getenv("SHOPIFY_WEBHOOK_SECRET")
        if webhook_secret:
            auth_header = request.headers.get("X-Webhook-Secret") or request.headers.get(
                "X-Shopify-Hmac-SHA256"
            )
            if auth_header != webhook_secret:
                return Response(
                    {"error": "Invalid webhook secret authorization"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        payload = request.data
        topic = payload.get("topic", "orders/fulfilled")
        order_data = payload.get("order", payload)

        order_id = order_data.get("order_id") or order_data.get("id")
        if not order_id:
            return Response(
                {"error": "order_id or id is required in payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer_info = order_data.get("customer", {})
        customer_email = customer_info.get("email") or order_data.get("email") or f"customer_{order_id}@example.com"
        customer_name = customer_info.get("name") or order_data.get("name") or "Valued Customer"

        customer, _ = Customer.objects.get_or_create(
            email=customer_email,
            defaults={
                "name": customer_name,
                "lifetime_value": Decimal(str(order_data.get("total", "0.00"))),
                "risk_score": 0.0,
            },
        )

        total_amount = Decimal(str(order_data.get("total", "0.00")))
        order_status = order_data.get("status", Order.Status.DELIVERED)
        now = timezone.now()

        order, created = Order.objects.update_or_create(
            order_id=str(order_id),
            defaults={
                "customer": customer,
                "total": total_amount,
                "status": order_status,
                "order_date": now,
                "delivered_date": now if order_status == Order.Status.DELIVERED else None,
            },
        )

        # Ingest items if provided
        items_data = order_data.get("items", [])
        if items_data:
            order.items.all().delete()
            calculated_total = Decimal("0.00")
            for item in items_data:
                sku = item.get("sku") or item.get("product_sku")
                if not sku:
                    logger.warning(
                        f"[WEBHOOK] Skipping order {order.order_id} item missing SKU: {item}"
                    )
                    continue
                product_name = item.get("name") or item.get("product_name") or f"Product {sku}"
                category = item.get("category", "accessories")
                price = Decimal(str(item.get("price", item.get("unit_price", "19.99"))))
                quantity = int(item.get("quantity", 1))

                product, _ = Product.objects.get_or_create(
                    sku=sku,
                    defaults={
                        "name": product_name,
                        "category": category,
                        "price": price,
                        "inventory_count": 50,
                        "description": f"Imported via webhook for SKU {sku}",
                    },
                )

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    unit_price=price,
                )
                calculated_total += price * quantity

            if total_amount == Decimal("0.00"):
                order.total = calculated_total
                order.save()

        logger.info(f"[WEBHOOK] Ingested topic '{topic}' for Order {order.order_id}")
        return Response(
            {
                "success": True,
                "topic": topic,
                "order_id": order.order_id,
                "created": created,
                "items_count": order.items.count(),
                "total": str(order.total),
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class AnalyticsView(APIView):
    """
    Aggregated return metrics and analytics for the merchant dashboard.
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        total_orders = Order.objects.count()
        total_returns = ReturnRequest.objects.count()
        total_customers = Customer.objects.count()
        return_rate = round((total_returns / total_orders * 100), 2) if total_orders > 0 else 0.0

        # Status distribution
        status_counts = (
            ReturnRequest.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Reason distribution
        reason_counts = (
            ReturnRequest.objects.values("reason_classified")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Total refunded value
        total_refunded = (
            RefundLedger.objects.filter(decision=RefundLedger.Decision.APPROVED)
            .aggregate(sum=Sum("amount"))["sum"]
            or Decimal("0.00")
        )

        # High risk customers count
        high_risk_count = Customer.objects.filter(risk_score__gt=0.7).count()

        return Response(
            {
                "total_orders": total_orders,
                "total_returns": total_returns,
                "total_customers": total_customers,
                "return_rate_percentage": return_rate,
                "total_refunded_amount": str(total_refunded),
                "high_risk_customers_count": high_risk_count,
                "returns_by_status": list(status_counts),
                "returns_by_reason": list(reason_counts),
            }
        )


class AgentSessionViewSet(viewsets.ModelViewSet):
    queryset = AgentSession.objects.all()
    serializer_class = AgentSessionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    lookup_field = "session_id"


class AgentChatView(APIView):
    """
    Chat endpoint for the ReturnPilot LangGraph ReAct agent.
    Accepts POST with message and optional session_id.
    Returns agent execution response with reasoning steps and HITL state.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        import uuid
        from django.http import StreamingHttpResponse
        from langchain_core.messages import HumanMessage
        from agent.graph import agent_app

        message_text = request.data.get("message", "").strip()
        session_id = request.data.get("session_id") or f"sess_{uuid.uuid4().hex[:12]}"
        stream_mode = request.data.get("stream", False) or request.query_params.get("stream") == "true"

        if not message_text:
            return Response(
                {"error": "message is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get or create session
        session, _ = AgentSession.objects.get_or_create(
            session_id=session_id,
            defaults={
                "title": message_text[:50] + ("..." if len(message_text) > 50 else ""),
                "messages": [],
            },
        )

        initial_state = {
            "messages": [HumanMessage(content=message_text)],
            "intermediate_steps": [],
            "hitl_pending": False,
            "hitl_details": None,
            "session_id": session_id,
        }

        config = {"configurable": {"thread_id": session_id}}

        try:
            result_state = agent_app.invoke(initial_state, config=config)
        except Exception as e:
            logger.error(f"Error executing agent graph: {e}")
            result_state = {
                "messages": [HumanMessage(content=message_text)],
                "intermediate_steps": [],
                "hitl_pending": False,
                "hitl_details": None,
            }

        # Extract final answer
        final_answer = ""
        msgs = result_state.get("messages", [])
        for m in reversed(msgs):
            if hasattr(m, "content") and m.content and not getattr(m, "tool_calls", None):
                final_answer = m.content
                break

        if not final_answer and msgs:
            final_answer = msgs[-1].content if hasattr(msgs[-1], "content") else str(msgs[-1])

        steps = result_state.get("intermediate_steps", [])
        hitl_pending = result_state.get("hitl_pending", False)
        hitl_details = result_state.get("hitl_details")

        # Save to session
        existing_history = list(session.messages)
        existing_history.append({"role": "user", "content": message_text, "timestamp": timezone.now().isoformat()})
        existing_history.append({
            "role": "assistant",
            "content": final_answer,
            "steps": steps,
            "hitl_pending": hitl_pending,
            "hitl_details": hitl_details,
            "timestamp": timezone.now().isoformat(),
        })

        session.messages = existing_history
        session.hitl_pending = hitl_pending
        session.hitl_data = hitl_details or {}
        session.save()

        response_data = {
            "session_id": session_id,
            "response": final_answer,
            "steps": steps,
            "hitl_pending": hitl_pending,
            "hitl_details": hitl_details,
        }

        if stream_mode:
            def event_stream():
                for step in steps:
                    chunk = json.dumps({"type": "tool_step", "step": step})
                    yield f"data: {chunk}\n\n"
                final_chunk = json.dumps({
                    "type": "final_response",
                    "session_id": session_id,
                    "response": final_answer,
                    "hitl_pending": hitl_pending,
                    "hitl_details": hitl_details,
                })
                yield f"data: {final_chunk}\n\n"

            return StreamingHttpResponse(event_stream(), content_type="text/event-stream")

        return Response(response_data, status=status.HTTP_200_OK)


class AgentApproveView(APIView):
    """
    Endpoint for merchant Human-In-The-Loop approval or rejection of flagged return refunds.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        from mcp_server.tools import process_refund

        session_id = request.data.get("session_id")
        return_id = request.data.get("return_id")
        decision = request.data.get("decision", "approved").lower()
        method = request.data.get("method", "original_payment")
        reason = request.data.get("reason", f"Merchant HITL manual decision: {decision}")

        if not return_id:
            return Response(
                {"error": "return_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not ReturnRequest.objects.filter(return_id__iexact=str(return_id).strip()).exists():
            return Response(
                {
                    "success": False,
                    "return_id": return_id,
                    "error": f"Return request '{return_id}' not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Force process refund overriding the HITL gate
        decision_code = "override_force_approve" if decision == "approved" else "rejected"
        result = process_refund(
            return_id=return_id,
            decision=decision_code,
            method=method,
            reason=reason,
        )

        # Update session if session_id provided
        if session_id:
            session = AgentSession.objects.filter(session_id=session_id).first()
            if session:
                session.hitl_pending = False
                existing_msgs = list(session.messages)
                existing_msgs.append({
                    "role": "assistant",
                    "content": f"Merchant has **{decision.upper()}** return `{return_id}`. Refund processed.",
                    "hitl_resolution": result,
                    "timestamp": timezone.now().isoformat(),
                })
                session.messages = existing_msgs
                session.save()

        return Response(
            {
                "success": True,
                "return_id": return_id,
                "decision": decision,
                "result": result,
            },
            status=status.HTTP_200_OK,
        )

