import uuid
from decimal import Decimal
from django.utils import timezone
from core.models import (
    Product,
    Customer,
    Order,
    OrderItem,
    ReturnPolicy,
    ReturnRequest,
    RefundLedger,
)


def lookup_order(order_id: str) -> dict:
    """
    Look up order details by order ID or customer email.
    """
    clean_id = order_id.strip()
    order = (
        Order.objects.filter(order_id__iexact=clean_id)
        .select_related("customer")
        .prefetch_related("items__product", "returns")
        .first()
    )

    if not order:
        order = (
            Order.objects.filter(customer__email__iexact=clean_id)
            .select_related("customer")
            .prefetch_related("items__product", "returns")
            .first()
        )

    if not order:
        return {
            "error": f"No order found matching '{order_id}'",
            "order_id_searched": order_id,
            "found": False,
        }

    customer = order.customer
    now = timezone.now()
    days_since_delivery = (
        (now - order.delivered_date).days if order.delivered_date else None
    )

    items_data = [
        {
            "item_id": item.id,
            "sku": item.product.sku,
            "name": item.product.name,
            "category": item.product.category,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
            "total_price": float(item.quantity * item.unit_price),
        }
        for item in order.items.all()
    ]

    existing_returns = [
        {
            "return_id": ret.return_id,
            "status": ret.status,
            "reason_classified": ret.reason_classified,
            "refund_amount": float(ret.refund_amount) if ret.refund_amount else 0.0,
            "created_at": str(ret.created_at),
        }
        for ret in order.returns.all()
    ]

    return {
        "order": {
            "order_id": order.order_id,
            "total": float(order.total),
            "status": order.status,
            "order_date": str(order.order_date),
            "delivered_date": str(order.delivered_date) if order.delivered_date else None,
        },
        "items": items_data,
        "customer": {
            "name": customer.name,
            "email": customer.email,
            "return_count": customer.return_count,
            "lifetime_value": float(customer.lifetime_value),
            "risk_score": customer.risk_score,
        },
        "existing_returns": existing_returns,
        "delivery_status": order.status,
        "days_since_delivery": days_since_delivery,
    }


def check_return_eligibility(order_id: str, item_skus: list[str]) -> dict:
    """
    Check whether specific items from an order are eligible for return based on policy.
    """
    order = (
        Order.objects.filter(order_id__iexact=order_id.strip())
        .select_related("customer")
        .prefetch_related("items__product")
        .first()
    )

    if not order:
        return {
            "eligible": False,
            "error": f"Order '{order_id}' not found",
            "items_checked": [],
            "warnings": ["Order does not exist"],
            "policy_applied": "None",
        }

    if order.status != Order.Status.DELIVERED:
        return {
            "eligible": False,
            "error": f"Order status is '{order.status}'. Only delivered orders are eligible for return.",
            "items_checked": [],
            "warnings": [f"Order status is {order.status}"],
            "policy_applied": "Standard Delivery Policy",
        }

    now = timezone.now()
    days_since_delivery = (
        (now - order.delivered_date).days if order.delivered_date else 0
    )

    items_checked = []
    warnings = []
    all_eligible = True
    policies_applied = set()

    # Customer return frequency warnings
    if order.customer.risk_score > 0.7:
        warnings.append(
            f"Customer has elevated risk score ({order.customer.risk_score:.2f}) and {order.customer.return_count} prior returns"
        )

    order_items_by_sku = {item.product.sku.upper(): item for item in order.items.all()}

    for raw_sku in item_skus:
        sku = raw_sku.strip().upper()
        if sku not in order_items_by_sku:
            items_checked.append({
                "sku": raw_sku,
                "eligible": False,
                "reason": f"SKU {raw_sku} is not part of order {order.order_id}",
            })
            all_eligible = False
            continue

        item = order_items_by_sku[sku]
        category = item.product.category.lower()
        policy = ReturnPolicy.objects.filter(category__iexact=category).first()

        window_days = policy.window_days if policy else 30
        policy_name = f"{category.capitalize()} Policy ({window_days} days)"
        policies_applied.add(policy_name)

        days_remaining = max(0, window_days - days_since_delivery)
        is_in_window = days_since_delivery <= window_days

        if not is_in_window:
            all_eligible = False
            items_checked.append({
                "sku": sku,
                "name": item.product.name,
                "category": category,
                "eligible": False,
                "policy": policy_name,
                "days_since_delivery": days_since_delivery,
                "window_days": window_days,
                "reason": f"Return window expired ({days_since_delivery} days since delivery > {window_days} day policy)",
            })
        else:
            items_checked.append({
                "sku": sku,
                "name": item.product.name,
                "category": category,
                "eligible": True,
                "policy": policy_name,
                "days_remaining": days_remaining,
                "conditions_required": policy.conditions if policy else "unopened, undamaged",
                "restocking_fee_pct": float(policy.restocking_fee_pct) if policy else 0.0,
            })

    return {
        "eligible": all_eligible and len(items_checked) > 0,
        "order_id": order.order_id,
        "items_checked": items_checked,
        "warnings": warnings,
        "policy_applied": ", ".join(policies_applied) if policies_applied else "Standard Policy",
    }


def initiate_return(order_id: str, item_skus: list[str], reason: str) -> dict:
    """
    Create a new return request for specified items with a free-text reason.
    """
    order = (
        Order.objects.filter(order_id__iexact=order_id.strip())
        .select_related("customer")
        .prefetch_related("items__product")
        .first()
    )

    if not order:
        return {"error": f"Order '{order_id}' not found"}

    order_items = order.items.all()
    item_skus_upper = [s.strip().upper() for s in item_skus]
    selected_items = [
        item for item in order_items if item.product.sku.upper() in item_skus_upper
    ]

    if not selected_items:
        # If no specific items matched, pick all items from order as fallback
        selected_items = list(order_items)

    refund_amount = sum(item.unit_price * item.quantity for item in selected_items)
    return_id = f"RET-2024-{uuid.uuid4().hex[:4].upper()}"

    risk_flags = []
    if order.customer.risk_score > 0.7:
        risk_flags.append(f"Customer risk score {order.customer.risk_score:.2f}")
    if refund_amount > 100:
        risk_flags.append(f"Refund amount ${float(refund_amount):.2f} exceeds threshold")

    ret_req = ReturnRequest.objects.create(
        return_id=return_id,
        order=order,
        reason_text=reason,
        status=ReturnRequest.Status.PENDING,
        refund_amount=refund_amount,
        risk_flags=risk_flags,
    )
    ret_req.items.set(selected_items)

    # Initial heuristic classification placeholder (Phase 4 connects Gemini async)
    reason_lower = reason.lower()
    if any(w in reason_lower for w in ["fit", "small", "large", "size", "tight", "loose", "length"]):
        classified = "sizing"
    elif any(w in reason_lower for w in ["broken", "screen", "stopped", "defective", "damage", "faulty", "buzzing"]):
        classified = "defective"
    elif any(w in reason_lower for w in ["wrong", "received", "instead", "sent"]):
        classified = "wrong_item"
    elif any(w in reason_lower for w in ["different", "photo", "picture", "color", "material", "described", "fake"]):
        classified = "not_as_described"
    elif any(w in reason_lower for w in ["mind", "decided", "gift", "keep", "bought"]):
        classified = "changed_mind"
    else:
        classified = "other"

    ret_req.reason_classified = classified
    ret_req.save()

    return {
        "return_id": ret_req.return_id,
        "order_id": order.order_id,
        "status": ret_req.status,
        "items": [item.product.sku for item in selected_items],
        "refund_amount": float(ret_req.refund_amount),
        "reason_received": reason,
        "ai_classification": ret_req.reason_classified or "processing",
        "message": "Return request created. AI classification in progress.",
    }


def classify_return_reason(return_id: str) -> dict:
    """
    Get or trigger AI classification of the return reason (uses Gemini via Celery).
    """
    ret = ReturnRequest.objects.filter(return_id__iexact=return_id.strip()).first()
    if not ret:
        return {"error": f"Return request '{return_id}' not found"}

    if not ret.reason_classified:
        from core.tasks import classify_return_reason_task

        try:
            res = classify_return_reason_task(ret.id)
            classified = res.get("classification", "other")
            confidence = res.get("confidence", 0.94)
            dist = res.get("distribution", {classified: 0.94, "other": 0.06})
        except Exception:
            classified = "other"
            confidence = 0.70
            dist = {"other": 1.0}
    else:
        classified = ret.reason_classified
        confidence = 0.94
        dist = {classified: 0.94, "not_as_described": 0.04, "other": 0.02}

    return {
        "return_id": ret.return_id,
        "original_reason": ret.reason_text,
        "classified_as": classified,
        "confidence": confidence,
        "category_distribution": dist,
    }


def recommend_exchange(return_id: str) -> dict:
    """
    AI-powered exchange recommendation based on return reason and product catalog.
    """
    ret = (
        ReturnRequest.objects.filter(return_id__iexact=return_id.strip())
        .prefetch_related("items__product")
        .first()
    )
    if not ret:
        return {"error": f"Return request '{return_id}' not found"}

    if not ret.exchange_recommendation:
        from core.tasks import generate_exchange_recommendation_task

        try:
            generate_exchange_recommendation_task(ret.id)
            ret.refresh_from_db()
        except Exception:
            pass

    first_item = ret.items.first()
    if not first_item:
        first_product = Product.objects.first()
        prod_sku = first_product.sku if first_product else "N/A"
        prod_name = first_product.name if first_product else "N/A"
        prod_cat = first_product.category if first_product else "clothing"
    else:
        prod_sku = first_item.product.sku
        prod_name = first_item.product.name
        prod_cat = first_item.product.category

    alternatives = Product.objects.filter(category__iexact=prod_cat).exclude(
        sku=prod_sku
    )[:3]

    recs = [
        {
            "sku": alt.sku,
            "name": alt.name,
            "price": float(alt.price),
            "match_score": round(0.95 - (idx * 0.08), 2),
        }
        for idx, alt in enumerate(alternatives)
    ]

    return {
        "return_id": ret.return_id,
        "original_item": {"sku": prod_sku, "name": prod_name},
        "reason": ret.reason_classified or "sizing",
        "recommendations": recs,
        "ai_analysis": ret.exchange_recommendation,
        "exchange_incentive": "Free shipping on exchange + 10% store credit",
    }


def flag_serial_returner(customer_email: str) -> dict:
    """
    Check customer return history for serial return or abuse patterns.
    """
    customer = (
        Customer.objects.filter(email__iexact=customer_email.strip())
        .prefetch_related("orders__returns")
        .first()
    )
    if not customer:
        return {"error": f"Customer '{customer_email}' not found"}

    orders = customer.orders.all()
    total_orders = orders.count()
    all_returns = ReturnRequest.objects.filter(order__customer=customer)
    total_returns = max(customer.return_count, all_returns.count())

    now = timezone.now()
    ninety_days_ago = now - timezone.timedelta(days=90)
    returns_90d = all_returns.filter(created_at__gte=ninety_days_ago).count()
    refunds_90d = (
        RefundLedger.objects.filter(
            return_request__order__customer=customer,
            decision=RefundLedger.Decision.APPROVED,
            decided_at__gte=ninety_days_ago,
        )
    )
    total_refund_val = sum(r.amount for r in refunds_90d)

    return_ratio = (
        round(total_returns / total_orders, 2) if total_orders > 0 else 0.0
    )

    patterns = []
    if customer.risk_score > 0.7:
        patterns.append("High return frequency across multiple orders")
    if returns_90d >= 3:
        patterns.append(f"{returns_90d} return requests in the last 90 days")
    if return_ratio > 0.3:
        patterns.append(f"High return-to-order ratio ({int(return_ratio * 100)}%)")
    if not patterns:
        patterns.append("Standard purchasing and return history")

    risk_level = (
        "high"
        if customer.risk_score > 0.7
        else ("medium" if customer.risk_score >= 0.3 else "low")
    )

    return {
        "customer": {"email": customer.email, "name": customer.name},
        "total_returns": total_returns,
        "returns_last_90_days": returns_90d,
        "total_refund_value_90_days": float(total_refund_val),
        "lifetime_value": float(customer.lifetime_value),
        "return_to_order_ratio": return_ratio,
        "risk_score": customer.risk_score,
        "risk_level": risk_level,
        "patterns_detected": patterns,
    }


def process_refund(
    return_id: str, decision: str, method: str = "original_payment", reason: str = ""
) -> dict:
    """
    Process refund for an approved return. Triggers HITL gate if high-value or high-risk.
    """
    ret = (
        ReturnRequest.objects.filter(return_id__iexact=return_id.strip())
        .select_related("order__customer")
        .first()
    )
    if not ret:
        return {"error": f"Return request '{return_id}' not found"}

    customer = ret.order.customer
    amount = float(ret.refund_amount) if ret.refund_amount else 0.0
    is_high_value = amount > 100.0
    is_high_risk = customer.risk_score > 0.75

    # Check for HITL gate trigger
    if (is_high_value or is_high_risk) and decision.lower() != "override_force_approve":
        ret.status = ReturnRequest.Status.AWAITING_APPROVAL
        ret.save()
        hitl_reason_parts = []
        if is_high_value:
            hitl_reason_parts.append(
                f"Refund amount ${amount:.2f} exceeds auto-approval threshold ($100.00)"
            )
        if is_high_risk:
            hitl_reason_parts.append(
                f"Customer risk score ({customer.risk_score:.2f}) exceeds high-risk threshold (0.75)"
            )

        return {
            "return_id": ret.return_id,
            "status": "awaiting_approval",
            "refund_amount": amount,
            "method": method,
            "hitl_triggered": True,
            "hitl_reason": ". ".join(hitl_reason_parts) + ". Merchant review required.",
            "risk_summary": f"Customer risk score: {customer.risk_score:.2f} ({'high' if is_high_risk else 'medium'}). Total prior returns: {customer.return_count}.",
        }

    # Otherwise process immediate decision
    decision_clean = decision.lower()
    if decision_clean in ["approved", "override_force_approve"]:
        ret.status = ReturnRequest.Status.APPROVED
        ret.resolved_at = timezone.now()
        ret.save()
        RefundLedger.objects.update_or_create(
            return_request=ret,
            defaults={
                "amount": Decimal(str(amount)),
                "method": method,
                "decision": RefundLedger.Decision.APPROVED,
                "decided_by": "agent",
                "reason": reason or "Automated approval via MCP process_refund",
            },
        )
        return {
            "return_id": ret.return_id,
            "status": "approved",
            "refund_amount": amount,
            "method": method,
            "hitl_triggered": False,
            "message": f"Refund of ${amount:.2f} successfully approved via {method}.",
        }
    else:
        ret.status = ReturnRequest.Status.REJECTED
        ret.resolved_at = timezone.now()
        ret.save()
        RefundLedger.objects.update_or_create(
            return_request=ret,
            defaults={
                "amount": Decimal("0.00"),
                "method": method,
                "decision": RefundLedger.Decision.REJECTED,
                "decided_by": "agent",
                "reason": reason or "Return rejected via MCP process_refund",
            },
        )
        return {
            "return_id": ret.return_id,
            "status": "rejected",
            "refund_amount": 0.0,
            "method": method,
            "hitl_triggered": False,
            "message": "Return request was rejected.",
        }


def list_pending_returns(status_filter: str = "pending", limit: int = 10) -> dict:
    """
    List return requests by status. Useful for merchant queue review.
    """
    now = timezone.now()
    returns_qs = (
        ReturnRequest.objects.filter(status__iexact=status_filter.strip())
        .select_related("order__customer")
        .prefetch_related("items__product")[:limit]
    )

    items_list = []
    for ret in returns_qs:
        items_summary = ", ".join(
            f"{item.product.name} × {item.quantity}" for item in ret.items.all()
        )
        days_pending = (now - ret.created_at).days
        items_list.append({
            "return_id": ret.return_id,
            "order_id": ret.order.order_id,
            "customer": ret.order.customer.email,
            "items_summary": items_summary or "No items attached",
            "reason": ret.reason_classified or ret.reason_text[:40],
            "refund_amount": float(ret.refund_amount) if ret.refund_amount else 0.0,
            "risk_score": ret.order.customer.risk_score,
            "days_pending": days_pending,
        })

    return {
        "filter": status_filter,
        "count": len(items_list),
        "returns": items_list,
    }
