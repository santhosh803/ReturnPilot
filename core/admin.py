from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    Product,
    Customer,
    Order,
    OrderItem,
    ReturnPolicy,
    ReturnRequest,
    RefundLedger,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["sku", "name", "category", "price", "inventory_count", "created_at"]
    list_filter = ["category", "created_at"]
    search_fields = ["sku", "name", "description"]
    ordering = ["category", "name"]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "email",
        "return_count",
        "lifetime_value",
        "risk_score_badge",
        "created_at",
    ]
    list_filter = ["created_at"]
    search_fields = ["name", "email"]
    readonly_fields = ["created_at"]

    @admin.display(description="Risk Score")
    def risk_score_badge(self, obj):
        score = obj.risk_score
        if score < 0.3:
            color = "#10b981"  # green
            label = f"{score:.2f} (Low)"
        elif score <= 0.7:
            color = "#f59e0b"  # yellow/orange
            label = f"{score:.2f} (Medium)"
        else:
            color = "#ef4444"  # red
            label = f"{score:.2f} (High)"
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 9999px; font-weight: 600; font-size: 11px;">{}</span>',
            color,
            label,
        )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ["product", "quantity", "unit_price"]


class ReturnRequestInline(admin.TabularInline):
    model = ReturnRequest
    extra = 0
    fields = ["return_id", "status", "reason_classified", "refund_amount", "created_at"]
    readonly_fields = ["return_id", "status", "reason_classified", "refund_amount", "created_at"]
    show_change_link = True


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_id",
        "customer_link",
        "total",
        "status_badge",
        "order_date",
        "delivered_date",
    ]
    list_filter = ["status", "order_date", "delivered_date"]
    search_fields = ["order_id", "customer__name", "customer__email"]
    inlines = [OrderItemInline, ReturnRequestInline]
    readonly_fields = ["created_at"]

    @admin.display(description="Customer")
    def customer_link(self, obj):
        url = reverse("admin:core_customer_change", args=[obj.customer.id])
        return format_html('<a href="{}">{}</a>', url, obj.customer.name)

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "pending": "#f59e0b",
            "shipped": "#3b82f6",
            "delivered": "#10b981",
            "cancelled": "#6b7280",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            obj.status.capitalize(),
        )


@admin.register(ReturnPolicy)
class ReturnPolicyAdmin(admin.ModelAdmin):
    list_display = [
        "category",
        "window_days",
        "restocking_fee_pct",
        "exchange_allowed",
        "conditions",
    ]
    list_filter = ["exchange_allowed"]
    search_fields = ["category", "conditions"]


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = [
        "return_id",
        "order_link",
        "customer_info",
        "status_badge",
        "reason_classified",
        "refund_amount",
        "customer_risk_badge",
        "created_at",
    ]
    list_filter = ["status", "reason_classified", "created_at"]
    search_fields = [
        "return_id",
        "order__order_id",
        "order__customer__name",
        "order__customer__email",
        "reason_text",
    ]
    readonly_fields = ["created_at"]
    actions = ["approve_returns", "reject_returns"]

    @admin.display(description="Order")
    def order_link(self, obj):
        url = reverse("admin:core_order_change", args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_id)

    @admin.display(description="Customer")
    def customer_info(self, obj):
        customer = obj.order.customer
        return f"{customer.name} ({customer.email})"

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "pending": "#f59e0b",
            "approved": "#10b981",
            "rejected": "#ef4444",
            "exchanged": "#8b5cf6",
            "awaiting_approval": "#f97316",
        }
        color = colors.get(obj.status, "#6b7280")
        label = obj.get_status_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            label,
        )

    @admin.display(description="Customer Risk")
    def customer_risk_badge(self, obj):
        score = obj.order.customer.risk_score
        if score < 0.3:
            color = "#10b981"
            label = f"{score:.2f} (Low)"
        elif score <= 0.7:
            color = "#f59e0b"
            label = f"{score:.2f} (Med)"
        else:
            color = "#ef4444"
            label = f"{score:.2f} (High)"
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 9999px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            label,
        )

    @admin.action(description="Approve selected returns and record refund")
    def approve_returns(self, request, queryset):
        count = 0
        for ret in queryset.filter(status__in=["pending", "awaiting_approval"]):
            ret.status = ReturnRequest.Status.APPROVED
            ret.resolved_at = timezone.now()
            ret.save()
            # If refund amount is set, create or update refund ledger
            amount = ret.refund_amount or 0
            RefundLedger.objects.update_or_create(
                return_request=ret,
                defaults={
                    "amount": amount,
                    "method": "original_payment",
                    "decision": RefundLedger.Decision.APPROVED,
                    "decided_by": request.user.email or request.user.username or "merchant_admin",
                    "reason": "Approved via admin action",
                },
            )
            count += 1
        self.message_user(request, f"{count} return(s) successfully approved.")

    @admin.action(description="Reject selected returns")
    def reject_returns(self, request, queryset):
        count = 0
        for ret in queryset.filter(status__in=["pending", "awaiting_approval"]):
            ret.status = ReturnRequest.Status.REJECTED
            ret.resolved_at = timezone.now()
            ret.save()
            RefundLedger.objects.update_or_create(
                return_request=ret,
                defaults={
                    "amount": 0,
                    "method": "original_payment",
                    "decision": RefundLedger.Decision.REJECTED,
                    "decided_by": request.user.email or request.user.username or "merchant_admin",
                    "reason": "Rejected via admin action",
                },
            )
            count += 1
        self.message_user(request, f"{count} return(s) rejected.")


@admin.register(RefundLedger)
class RefundLedgerAdmin(admin.ModelAdmin):
    list_display = [
        "return_request_link",
        "amount",
        "method",
        "decision_badge",
        "decided_by",
        "decided_at",
    ]
    list_filter = ["decision", "method", "decided_at"]
    search_fields = ["return_request__return_id", "decided_by", "reason"]
    readonly_fields = [
        "return_request",
        "amount",
        "method",
        "decision",
        "decided_by",
        "reason",
        "decided_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Return Request")
    def return_request_link(self, obj):
        url = reverse("admin:core_returnrequest_change", args=[obj.return_request.id])
        return format_html('<a href="{}">{}</a>', url, obj.return_request.return_id)

    @admin.display(description="Decision")
    def decision_badge(self, obj):
        color = "#10b981" if obj.decision == "approved" else "#ef4444"
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            obj.decision.capitalize(),
        )
