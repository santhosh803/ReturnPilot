from rest_framework import serializers
from .models import (
    Product,
    Customer,
    Order,
    OrderItem,
    ReturnPolicy,
    ReturnRequest,
    RefundLedger,
)


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "category",
            "price",
            "inventory_count",
            "description",
            "created_at",
        ]


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id",
            "email",
            "name",
            "return_count",
            "lifetime_value",
            "risk_score",
            "created_at",
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_category = serializers.CharField(source="product.category", read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_sku",
            "product_name",
            "product_category",
            "quantity",
            "unit_price",
            "total_price",
        ]

    def get_total_price(self, obj):
        return str(obj.quantity * obj.unit_price)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_email = serializers.CharField(source="customer.email", read_only=True)
    customer_risk_score = serializers.FloatField(
        source="customer.risk_score", read_only=True
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "order_id",
            "customer",
            "customer_name",
            "customer_email",
            "customer_risk_score",
            "total",
            "status",
            "order_date",
            "delivered_date",
            "created_at",
            "items",
        ]


class ReturnPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnPolicy
        fields = [
            "id",
            "category",
            "window_days",
            "conditions",
            "restocking_fee_pct",
            "exchange_allowed",
        ]


class RefundLedgerSerializer(serializers.ModelSerializer):
    return_id = serializers.CharField(
        source="return_request.return_id", read_only=True
    )

    class Meta:
        model = RefundLedger
        fields = [
            "id",
            "return_request",
            "return_id",
            "amount",
            "method",
            "decision",
            "decided_by",
            "reason",
            "decided_at",
        ]


class ReturnRequestSerializer(serializers.ModelSerializer):
    order_id_code = serializers.CharField(source="order.order_id", read_only=True)
    customer_name = serializers.CharField(
        source="order.customer.name", read_only=True
    )
    customer_email = serializers.CharField(
        source="order.customer.email", read_only=True
    )
    customer_risk_score = serializers.FloatField(
        source="order.customer.risk_score", read_only=True
    )
    items_detail = OrderItemSerializer(source="items", many=True, read_only=True)
    refund = RefundLedgerSerializer(read_only=True)

    class Meta:
        model = ReturnRequest
        fields = [
            "id",
            "return_id",
            "order",
            "order_id_code",
            "customer_name",
            "customer_email",
            "customer_risk_score",
            "items",
            "items_detail",
            "reason_text",
            "reason_classified",
            "status",
            "refund_amount",
            "exchange_recommendation",
            "risk_flags",
            "created_at",
            "resolved_at",
            "refund",
        ]
        extra_kwargs = {
            "items": {"write_only": False},
        }
