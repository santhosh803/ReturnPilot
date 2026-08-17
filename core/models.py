from django.db import models
import uuid


class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)  # electronics, clothing, home, beauty, etc.
    price = models.DecimalField(max_digits=10, decimal_places=2)
    inventory_count = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sku} — {self.name}"


class Customer(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    return_count = models.IntegerField(default=0)
    lifetime_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    risk_score = models.FloatField(default=0.0)  # 0.0 (safe) to 1.0 (high-risk serial returner)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.email})"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        SHIPPED = "shipped"
        DELIVERED = "delivered"
        CANCELLED = "cancelled"

    order_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    order_date = models.DateTimeField()
    delivered_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-order_date"]

    def __str__(self):
        return f"Order {self.order_id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x{self.quantity} in {self.order.order_id}"


class ReturnPolicy(models.Model):
    category = models.CharField(max_length=100, unique=True)  # matches Product.category
    window_days = models.IntegerField(default=30)
    conditions = models.TextField(help_text="Comma-separated conditions: unused, tags_attached, original_packaging")
    restocking_fee_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    exchange_allowed = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Return Policies"
        ordering = ["category"]

    def __str__(self):
        return f"{self.category} — {self.window_days} day window"


class ReturnRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        APPROVED = "approved"
        REJECTED = "rejected"
        EXCHANGED = "exchanged"
        AWAITING_APPROVAL = "awaiting_approval"  # HITL gate

    class Reason(models.TextChoices):
        SIZING = "sizing"
        DEFECTIVE = "defective"
        CHANGED_MIND = "changed_mind"
        WRONG_ITEM = "wrong_item"
        NOT_AS_DESCRIBED = "not_as_described"
        OTHER = "other"

    return_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="returns")
    items = models.ManyToManyField(OrderItem, related_name="return_requests")
    reason_text = models.TextField(help_text="Free-text reason from customer")
    reason_classified = models.CharField(max_length=30, choices=Reason.choices, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    exchange_recommendation = models.TextField(blank=True)
    risk_flags = models.JSONField(default=list, blank=True)  # list of warning strings
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Return {self.return_id} — {self.status}"


class RefundLedger(models.Model):
    class Decision(models.TextChoices):
        APPROVED = "approved"
        REJECTED = "rejected"

    return_request = models.OneToOneField(ReturnRequest, on_delete=models.CASCADE, related_name="refund")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=50, default="original_payment")  # original_payment, store_credit
    decision = models.CharField(max_length=20, choices=Decision.choices)
    decided_by = models.CharField(max_length=100)  # "agent" or merchant email
    reason = models.TextField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-decided_at"]

    def __str__(self):
        return f"Refund {self.decision} — ${self.amount} for {self.return_request.return_id}"


class AgentSession(models.Model):
    session_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    title = models.CharField(max_length=255, default="Returns Assistance")
    messages = models.JSONField(default=list, blank=True)
    hitl_pending = models.BooleanField(default=False)
    hitl_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Session {self.session_id} ({self.title})"

