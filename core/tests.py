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

    def test_mcp_tools_suite(self):
        from mcp_server import tools

        # 1. lookup_order
        lookup_res = tools.lookup_order("ORD-TEST-0001")
        self.assertEqual(lookup_res["order"]["order_id"], "ORD-TEST-0001")
        self.assertEqual(len(lookup_res["items"]), 1)
        self.assertEqual(lookup_res["customer"]["email"], "testcustomer@example.com")

        # 2. check_return_eligibility
        elig_res = tools.check_return_eligibility("ORD-TEST-0001", ["TEST-SHIRT-01"])
        self.assertTrue(elig_res["eligible"])
        self.assertEqual(len(elig_res["items_checked"]), 1)

        # 3. initiate_return
        init_res = tools.initiate_return(
            "ORD-TEST-0001",
            ["TEST-SHIRT-01"],
            "The shirt was too tight and small",
        )
        self.assertIn("return_id", init_res)
        self.assertEqual(init_res["ai_classification"], "sizing")
        created_ret_id = init_res["return_id"]

        # 4. classify_return_reason
        class_res = tools.classify_return_reason(created_ret_id)
        self.assertEqual(class_res["classified_as"], "sizing")
        self.assertEqual(class_res["confidence"], 0.94)

        # 5. recommend_exchange
        rec_res = tools.recommend_exchange(created_ret_id)
        self.assertEqual(rec_res["return_id"], created_ret_id)
        self.assertIn("recommendations", rec_res)

        # 6. flag_serial_returner
        flag_res = tools.flag_serial_returner("testcustomer@example.com")
        self.assertEqual(flag_res["customer"]["email"], "testcustomer@example.com")
        self.assertIn(flag_res["risk_level"], ["low", "medium", "high"])

        # 7. process_refund (verify HITL gate triggers for high-risk customer)
        refund_res = tools.process_refund(created_ret_id, "approved")
        self.assertTrue(refund_res["hitl_triggered"])
        self.assertEqual(refund_res["status"], "awaiting_approval")

        # 7b. process_refund (low risk customer auto approval)
        self.customer.risk_score = 0.1
        self.customer.save()
        low_risk_refund = tools.process_refund(created_ret_id, "approved")
        self.assertFalse(low_risk_refund["hitl_triggered"])
        self.assertEqual(low_risk_refund["status"], "approved")

        # 8. list_pending_returns
        list_res = tools.list_pending_returns("approved")
        self.assertTrue(list_res["count"] >= 1)

    def test_celery_ai_tasks(self):
        from core.tasks import (
            classify_return_reason_task,
            generate_exchange_recommendation_task,
        )

        ret = ReturnRequest.objects.create(
            return_id="RET-CELERY-001",
            order=self.order,
            reason_text="The shirt was completely torn at the seam when opened.",
            status=ReturnRequest.Status.PENDING,
        )
        ret.items.add(self.order_item)

        # Run classification task
        res_class = classify_return_reason_task(ret.id)
        ret.refresh_from_db()
        self.assertEqual(ret.reason_classified, "defective")
        self.assertEqual(res_class["classification"], "defective")

        # Run exchange recommendation task
        res_rec = generate_exchange_recommendation_task(ret.id)
        ret.refresh_from_db()
        self.assertTrue(len(ret.exchange_recommendation) > 0)
        self.assertIn("recommendation", res_rec)


