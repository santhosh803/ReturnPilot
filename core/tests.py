from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from .models import (
    Product,
    Customer,
    Order,
    OrderItem,
    ReturnPolicy,
    ReturnRequest,
    RefundLedger,
)


class CoreModelAndAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create policy
        self.policy = ReturnPolicy.objects.create(
            category="clothing",
            window_days=30,
            conditions="unworn, tags_attached",
            restocking_fee_pct=Decimal("0.00"),
            exchange_allowed=True,
        )

        # Create product
        self.product = Product.objects.create(
            sku="TEST-SHIRT-01",
            name="Test Cotton Shirt",
            category="clothing",
            price=Decimal("49.99"),
            inventory_count=20,
            description="Test description",
        )

        # Create customer
        self.customer = Customer.objects.create(
            email="testcustomer@example.com",
            name="Alice Test",
            return_count=1,
            lifetime_value=Decimal("150.00"),
            risk_score=0.15,
        )

        # Create order
        self.order = Order.objects.create(
            order_id="ORD-TEST-0001",
            customer=self.customer,
            total=Decimal("49.99"),
            status=Order.Status.DELIVERED,
            order_date=timezone.now() - timezone.timedelta(days=10),
            delivered_date=timezone.now() - timezone.timedelta(days=8),
        )

        # Create order item
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            unit_price=Decimal("49.99"),
        )

    def test_model_str_representations(self):
        self.assertEqual(str(self.product), "TEST-SHIRT-01 — Test Cotton Shirt")
        self.assertEqual(str(self.customer), "Alice Test (testcustomer@example.com)")
        self.assertEqual(str(self.order), "Order ORD-TEST-0001")
        self.assertEqual(
            str(self.order_item),
            "Test Cotton Shirt x1 in ORD-TEST-0001",
        )
        self.assertEqual(str(self.policy), "clothing — 30 day window")

    def test_api_products_list_and_retrieve(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertTrue(len(results) >= 1)

        detail_response = self.client.get(f"/api/products/{self.product.id}/")
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["sku"], "TEST-SHIRT-01")

    def test_api_customers_list_and_retrieve(self):
        response = self.client.get("/api/customers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertTrue(len(results) >= 1)

    def test_api_orders_list(self):
        response = self.client.get("/api/orders/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertTrue(len(results) >= 1)
        self.assertEqual(results[0]["order_id"], "ORD-TEST-0001")
        self.assertEqual(len(results[0]["items"]), 1)

    def test_return_request_creation_and_signal(self):
        # Create return request
        ret = ReturnRequest.objects.create(
            return_id="RET-TEST-0001",
            order=self.order,
            reason_text="Size too small",
            reason_classified=ReturnRequest.Reason.SIZING,
            status=ReturnRequest.Status.PENDING,
            refund_amount=Decimal("49.99"),
        )
        ret.items.add(self.order_item)

        response = self.client.get("/api/returns/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertTrue(len(results) >= 1)
        self.assertEqual(results[0]["return_id"], "RET-TEST-0001")

    def test_webhook_shopify_ingestion(self):
        payload = {
            "topic": "orders/fulfilled",
            "order": {
                "order_id": "ORD-SHOPIFY-9999",
                "total": "99.98",
                "status": "delivered",
                "customer": {
                    "email": "shopify_shopper@example.com",
                    "name": "Shopify Shopper",
                },
                "items": [
                    {
                        "sku": "TEST-SHIRT-01",
                        "name": "Test Cotton Shirt",
                        "category": "clothing",
                        "price": "49.99",
                        "quantity": 2,
                    }
                ],
            },
        }

        response = self.client.post(
            "/api/webhooks/shopify/",
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Order.objects.filter(order_id="ORD-SHOPIFY-9999").exists())
        order = Order.objects.get(order_id="ORD-SHOPIFY-9999")
        self.assertEqual(order.customer.email, "shopify_shopper@example.com")
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().quantity, 2)

    def test_analytics_endpoint(self):
        response = self.client.get("/api/analytics/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_orders", response.data)
        self.assertIn("total_returns", response.data)
        self.assertIn("return_rate_percentage", response.data)
