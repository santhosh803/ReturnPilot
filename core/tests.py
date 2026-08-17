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

    def test_webhook_rejects_invalid_secret_header(self):
        """When SHOPIFY_WEBHOOK_SECRET is set, requests without a matching header must be rejected."""
        import os
        from unittest.mock import patch

        payload = {
            "topic": "orders/fulfilled",
            "order": {
                "order_id": "ORD-SECURED-0001",
                "total": "25.00",
                "status": "delivered",
                "customer": {"email": "secured@example.com", "name": "Secured Shopper"},
                "items": [
                    {
                        "sku": "TEST-SHIRT-01",
                        "name": "Test Cotton Shirt",
                        "category": "clothing",
                        "price": "25.00",
                        "quantity": 1,
                    }
                ],
            },
        }

        with patch.dict(os.environ, {"SHOPIFY_WEBHOOK_SECRET": "top-secret-shared-key"}):
            # Missing header
            resp_missing = self.client.post(
                "/api/webhooks/shopify/", data=payload, format="json"
            )
            self.assertEqual(resp_missing.status_code, status.HTTP_401_UNAUTHORIZED)

            # Wrong header
            resp_wrong = self.client.post(
                "/api/webhooks/shopify/",
                data=payload,
                format="json",
                HTTP_X_WEBHOOK_SECRET="not-the-right-secret",
            )
            self.assertEqual(resp_wrong.status_code, status.HTTP_401_UNAUTHORIZED)

            # Correct header allows ingestion through
            resp_ok = self.client.post(
                "/api/webhooks/shopify/",
                data=payload,
                format="json",
                HTTP_X_WEBHOOK_SECRET="top-secret-shared-key",
            )
            self.assertEqual(resp_ok.status_code, status.HTTP_201_CREATED)
            self.assertTrue(Order.objects.filter(order_id="ORD-SECURED-0001").exists())

    def test_agent_approve_rejects_unknown_return_id(self):
        """Approve endpoint must return 404 for a return_id that does not exist."""
        approve_payload = {
            "session_id": "sess-unknown-return",
            "return_id": "RET-DOES-NOT-EXIST-9999",
            "decision": "approved",
        }
        resp = self.client.post(
            "/api/agent/approve/", data=approve_payload, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(resp.data.get("success"))
        self.assertIn("not found", resp.data.get("error", "").lower())

    def test_check_return_eligibility_rejects_final_sale_and_hygiene(self):
        """Policies whose conditions include final_sale/hygiene_seal_broken markers must block returns."""
        from mcp_server import tools

        # Final sale category
        ReturnPolicy.objects.create(
            category="clearance",
            window_days=30,
            conditions="unused, final_sale, no_returns",
            restocking_fee_pct=Decimal("0.00"),
            exchange_allowed=False,
        )
        clearance_product = Product.objects.create(
            sku="CLEAR-001",
            name="Clearance Sweater",
            category="clearance",
            price=Decimal("15.00"),
            inventory_count=5,
        )
        clearance_order = Order.objects.create(
            order_id="ORD-CLEAR-01",
            customer=self.customer,
            total=Decimal("15.00"),
            status=Order.Status.DELIVERED,
            order_date=timezone.now() - timezone.timedelta(days=5),
            delivered_date=timezone.now() - timezone.timedelta(days=3),
        )
        OrderItem.objects.create(
            order=clearance_order,
            product=clearance_product,
            quantity=1,
            unit_price=Decimal("15.00"),
        )

        clear_res = tools.check_return_eligibility("ORD-CLEAR-01", ["CLEAR-001"])
        self.assertFalse(clear_res["eligible"])
        checked = clear_res["items_checked"][0]
        self.assertFalse(checked["eligible"])
        self.assertEqual(checked["policy_condition_violated"], "final_sale")
        self.assertIn("prohibits", checked["reason"].lower())

        # Hygiene-sealed personal-care category
        ReturnPolicy.objects.create(
            category="personal_care",
            window_days=30,
            conditions="sealed, hygiene_seal_broken",
            restocking_fee_pct=Decimal("0.00"),
            exchange_allowed=False,
        )
        hygiene_product = Product.objects.create(
            sku="HYG-001",
            name="Sealed Personal Care Item",
            category="personal_care",
            price=Decimal("22.00"),
            inventory_count=10,
        )
        hygiene_order = Order.objects.create(
            order_id="ORD-HYG-01",
            customer=self.customer,
            total=Decimal("22.00"),
            status=Order.Status.DELIVERED,
            order_date=timezone.now() - timezone.timedelta(days=4),
            delivered_date=timezone.now() - timezone.timedelta(days=2),
        )
        OrderItem.objects.create(
            order=hygiene_order,
            product=hygiene_product,
            quantity=1,
            unit_price=Decimal("22.00"),
        )

        hygiene_res = tools.check_return_eligibility("ORD-HYG-01", ["HYG-001"])
        self.assertFalse(hygiene_res["eligible"])
        hchecked = hygiene_res["items_checked"][0]
        self.assertEqual(hchecked["policy_condition_violated"], "hygiene_seal_broken")

    def test_agent_chat_and_hitl_endpoints(self):
        # 1. Chat endpoint invocation
        chat_payload = {
            "message": "Process the return for order ORD-TEST-0001 because the size was too small",
            "session_id": "test-session-123",
        }
        chat_resp = self.client.post("/api/agent/chat/", data=chat_payload, format="json")
        self.assertEqual(chat_resp.status_code, status.HTTP_200_OK)
        self.assertIn("session_id", chat_resp.data)
        self.assertIn("response", chat_resp.data)
        self.assertTrue(len(chat_resp.data["steps"]) >= 1)

        # 2. Session list endpoint
        sess_resp = self.client.get("/api/agent/sessions/")
        self.assertEqual(sess_resp.status_code, status.HTTP_200_OK)

        # 3. Approve endpoint invocation — first create the return so the approve target exists
        pending_return = ReturnRequest.objects.create(
            return_id="RET-TEST-0001",
            order=self.order,
            reason_text="Size was too small",
            reason_classified=ReturnRequest.Reason.SIZING,
            status=ReturnRequest.Status.AWAITING_APPROVAL,
            refund_amount=Decimal("49.99"),
        )
        pending_return.items.add(self.order_item)

        approve_payload = {
            "session_id": "test-session-123",
            "return_id": "RET-TEST-0001",
            "decision": "approved",
            "method": "original_payment",
            "reason": "Merchant approved manually in test",
        }
        appr_resp = self.client.post("/api/agent/approve/", data=approve_payload, format="json")
        self.assertEqual(appr_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(appr_resp.data["success"])



