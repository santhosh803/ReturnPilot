import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from core.models import (
    Product,
    Customer,
    Order,
    OrderItem,
    ReturnPolicy,
    ReturnRequest,
    RefundLedger,
)


class Command(BaseCommand):
    help = "Seed the database with realistic demo data (policies, products, customers, orders, returns, refunds)"

    def handle(self, *args, **options):
        self.stdout.write("Starting database seeding...")
        fake = Faker()
        Faker.seed(42)
        random.seed(42)

        # 1. Return Policies
        self.stdout.write("Creating return policies...")
        policies_data = [
            {
                "category": "electronics",
                "window_days": 30,
                "conditions": "original_packaging, all_accessories_included, undamaged",
                "restocking_fee_pct": Decimal("10.00"),
                "exchange_allowed": True,
            },
            {
                "category": "clothing",
                "window_days": 30,
                "conditions": "unworn, tags_attached, original_packaging",
                "restocking_fee_pct": Decimal("0.00"),
                "exchange_allowed": True,
            },
            {
                "category": "home",
                "window_days": 45,
                "conditions": "unused, original_box, undamaged",
                "restocking_fee_pct": Decimal("5.00"),
                "exchange_allowed": True,
            },
            {
                "category": "beauty",
                "window_days": 14,
                "conditions": "unopened, sealed, unused",
                "restocking_fee_pct": Decimal("0.00"),
                "exchange_allowed": False,
            },
            {
                "category": "food",
                "window_days": 7,
                "conditions": "unopened, perishable_guidelines",
                "restocking_fee_pct": Decimal("0.00"),
                "exchange_allowed": False,
            },
            {
                "category": "accessories",
                "window_days": 30,
                "conditions": "unused, tags_attached, original_pouch",
                "restocking_fee_pct": Decimal("0.00"),
                "exchange_allowed": True,
            },
        ]

        for p_data in policies_data:
            ReturnPolicy.objects.update_or_create(
                category=p_data["category"],
                defaults=p_data,
            )

        # 2. 50 Products
        self.stdout.write("Creating 50 products...")
        catalog = [
            # Clothing (15 items)
            ("SHIRT-BLU-S", "Classic Oxford Shirt — Small / Blue", "clothing", "49.99", 40, "Premium breathable 100% cotton button-down shirt."),
            ("SHIRT-BLU-M", "Classic Oxford Shirt — Medium / Blue", "clothing", "49.99", 35, "Premium breathable 100% cotton button-down shirt."),
            ("SHIRT-BLU-L", "Classic Oxford Shirt — Large / Blue", "clothing", "49.99", 30, "Premium breathable 100% cotton button-down shirt."),
            ("SHIRT-BLU-XL", "Classic Oxford Shirt — XL / Blue", "clothing", "49.99", 20, "Premium breathable 100% cotton button-down shirt."),
            ("SHIRT-WHT-S", "Classic Oxford Shirt — Small / White", "clothing", "49.99", 45, "Crisp white cotton everyday button-down shirt."),
            ("SHIRT-WHT-M", "Classic Oxford Shirt — Medium / White", "clothing", "49.99", 50, "Crisp white cotton everyday button-down shirt."),
            ("SHIRT-WHT-L", "Classic Oxford Shirt — Large / White", "clothing", "49.99", 40, "Crisp white cotton everyday button-down shirt."),
            ("JEANS-SLM-30", "Slim-Fit Stretch Denim — 30x32", "clothing", "69.99", 25, "Mid-rise dark wash denim with comfortable stretch."),
            ("JEANS-SLM-32", "Slim-Fit Stretch Denim — 32x32", "clothing", "69.99", 30, "Mid-rise dark wash denim with comfortable stretch."),
            ("JEANS-SLM-34", "Slim-Fit Stretch Denim — 34x32", "clothing", "69.99", 25, "Mid-rise dark wash denim with comfortable stretch."),
            ("HOODIE-GRY-M", "Heavyweight Fleece Hoodie — Medium / Grey", "clothing", "59.99", 35, "Warm brushed cotton-poly blend fleece hoodie."),
            ("HOODIE-GRY-L", "Heavyweight Fleece Hoodie — Large / Grey", "clothing", "59.99", 30, "Warm brushed cotton-poly blend fleece hoodie."),
            ("JACKET-BLK-M", "Waterproof Rain Jacket — Medium / Black", "clothing", "119.99", 15, "Breathable 2.5-layer waterproof shell jacket."),
            ("JACKET-BLK-L", "Waterproof Rain Jacket — Large / Black", "clothing", "119.99", 20, "Breathable 2.5-layer waterproof shell jacket."),
            ("DRESS-FLR-S", "Floral Summer Wrap Dress — Small", "clothing", "79.99", 18, "Lightweight woven viscose wrap dress."),

            # Electronics (12 items)
            ("ELEC-HDPH-01", "AeroSound Pro Noise-Cancelling Headphones", "electronics", "249.99", 25, "Active noise cancelling with 40h battery life."),
            ("ELEC-EARB-01", "TrueSound Wireless Earbuds with Charging Case", "electronics", "89.99", 50, "IPX7 waterproof earbuds with rich bass."),
            ("ELEC-SPKR-01", "PulseWave 360 Portable Bluetooth Speaker", "electronics", "79.99", 40, "Deep 360-degree sound with 15-hour playback."),
            ("ELEC-SMWT-01", "FitPulse GPS Smart Fitness Watch — Black", "electronics", "179.99", 30, "Heart rate, SpO2, GPS tracking, 7-day battery."),
            ("ELEC-CHRG-01", "3-in-1 Fast Wireless Charging Station", "electronics", "45.99", 60, "Charge phone, smartwatch, and earbuds simultaneously."),
            ("ELEC-PBANK-01", "UltraCharge 20000mAh Power Bank (65W)", "electronics", "59.99", 45, "USB-C PD high-speed laptop and mobile power bank."),
            ("ELEC-KEYB-01", "Mechanical RGB Gaming Keyboard (Brown Switches)", "electronics", "99.99", 25, "Hot-swappable mechanical switches with aluminum frame."),
            ("ELEC-MOUS-01", "Ergonomic Precision Wireless Mouse", "electronics", "49.99", 35, "Quiet-click contoured design with high-DPI optical sensor."),
            ("ELEC-WEBC-01", "ClearView 4K Ultra HD Webcam with Mic", "electronics", "89.99", 20, "Auto-focus 4K conference webcam with dual stereo mics."),
            ("ELEC-MIC-01", "StudioStream USB Condenser Microphone", "electronics", "69.99", 30, "Cardioid pattern for podcasting, streaming, and vocals."),
            ("ELEC-HUB-01", "7-in-1 USB-C Hub Adapter 4K HDMI", "electronics", "39.99", 50, "HDMI 4K, 100W PD passthrough, SD card reader, 3x USB 3.0."),
            ("ELEC-LIGHT-01", "Smart ScreenBar LED Monitor Light", "electronics", "54.99", 40, "Auto-dimming glare-free asymmetric monitor light."),

            # Home (9 items)
            ("HOME-KETT-01", "Precision Gooseneck Electric Kettle (1L)", "home", "64.99", 25, "Variable temperature control with 1-hour keep-warm."),
            ("HOME-DIFF-01", "Ultrasonic Ceramic Aromatherapy Diffuser", "home", "39.99", 30, "Whisper-quiet misting with warm ambient LED light."),
            ("HOME-PILL-01", "Ergonomic Contour Memory Foam Pillow", "home", "49.99", 45, "Cooling gel infused cervical spine support pillow."),
            ("HOME-BLNK-01", "Weighted Gravity Blanket — 15 lbs / Grey", "home", "89.99", 20, "100% breathable cotton micro-glass bead weighted blanket."),
            ("HOME-ROBT-01", "Smart Robot Vacuum & Mop Combo", "home", "299.99", 12, "LiDAR navigation, 3000Pa suction power, app control."),
            ("HOME-AIRP-01", "True HEPA Air Purifier for Large Rooms", "home", "139.99", 18, "Removes 99.97% airborne allergens, smoke, and odors."),
            ("HOME-MUG-01", "Smart Temperature Control Heated Mug (12oz)", "home", "99.99", 22, "Keeps drinks at perfect temperature for up to 2 hours."),
            ("HOME-KNIF-01", "Japanese Damascus Chef's Knife (8-inch)", "home", "79.99", 28, "67-layer VG-10 steel razor sharp culinary knife."),
            ("HOME-PLAN-01", "Self-Watering Ceramic Indoor Plant Pot", "home", "29.99", 40, "Modern minimalist glazed pot with sub-irrigation."),

            # Beauty (6 items)
            ("BEAU-SERM-01", "HydraGlow Vitamin C + Hyaluronic Acid Serum", "beauty", "34.99", 60, "Anti-aging brightening daily facial serum (30ml)."),
            ("BEAU-CREM-01", "Overnight Peptide Repair Night Cream", "beauty", "42.99", 45, "Deep hydration renewing barrier cream (50ml)."),
            ("BEAU-SUN-01", "Invisible Daily Mineral Sunscreen SPF 50", "beauty", "26.99", 75, "Non-greasy, zero white cast broad-spectrum UV shield."),
            ("BEAU-DRYR-01", "Ionic High-Speed Hair Dryer with Diffuser", "beauty", "129.99", 20, "110,000 RPM brushless motor fast drying hair tool."),
            ("BEAU-MASK-01", "Detoxifying French Green Clay Face Mask", "beauty", "24.99", 50, "Pore-clearing natural purifying treatment (100g)."),
            ("BEAU-LIPO-01", "Nourishing Peptide Lip Tint — Rosewood", "beauty", "18.99", 80, "Sheer hydrating plumping lip balm with organic oils."),

            # Food (4 items)
            ("FOOD-COFF-01", "Single-Origin Ethiopian Yirgacheffe Whole Beans (12oz)", "food", "19.99", 50, "Light roast floral and citrus notes specialty coffee."),
            ("FOOD-MATC-01", "Ceremonial Grade Uji Matcha Green Tea (30g)", "food", "27.99", 40, "Stone-ground first harvest Kyoto ceremonial matcha."),
            ("FOOD-CHOC-01", "Artisan Single-Origin Dark Chocolate Gift Box (8ct)", "food", "24.99", 35, "Handcrafted 72% fair-trade truffles and bars."),
            ("FOOD-HONEY-01", "Raw Manuka Honey MGO 400+ (250g)", "food", "44.99", 30, "Certified 100% pure authentic New Zealand manuka honey."),

            # Accessories (4 items)
            ("ACC-WLGR-01", "RFID Slim Minimalist Leather Wallet — Brown", "accessories", "39.99", 50, "Full-grain vegetable tanned bifold front-pocket wallet."),
            ("ACC-SUNG-01", "Polarized Aviator Sunglasses UV400", "accessories", "59.99", 35, "Titanium frame with anti-reflective polarized lenses."),
            ("ACC-BACK-01", "CityCommute Water-Resistant Laptop Backpack (22L)", "accessories", "89.99", 25, "Padded compartment for 16-inch laptops with luggage strap."),
            ("ACC-BELT-01", "Reversible Italian Leather Dress Belt (Black/Brown)", "accessories", "34.99", 40, "Durable stainless steel rotating buckle leather belt."),
        ]

        products = []
        for sku, name, cat, price, inv, desc in catalog:
            prod, _ = Product.objects.update_or_create(
                sku=sku,
                defaults={
                    "name": name,
                    "category": cat,
                    "price": Decimal(price),
                    "inventory_count": inv,
                    "description": desc,
                },
            )
            products.append(prod)

        # 3. 100 Customers
        self.stdout.write("Creating 100 customers...")
        customers = []
        # Distinct high-risk profiles
        high_risk_names = [
            ("Victoria Vance", "victoria.vance@example.com", 8, Decimal("3200.00"), 0.88),
            ("Marcus Sterling", "marcus.sterling@example.com", 6, Decimal("1850.00"), 0.82),
            ("Chloe Davenport", "chloe.davenport@example.com", 9, Decimal("4100.00"), 0.92),
            ("Brandon Hayes", "brandon.hayes@example.com", 5, Decimal("1400.00"), 0.78),
            ("Rachel Zimmerman", "rachel.z@example.com", 7, Decimal("2600.00"), 0.85),
            ("Derek Callahan", "derek.callahan@example.com", 6, Decimal("1950.00"), 0.81),
            ("Samantha Brooks", "samantha.brooks@example.com", 10, Decimal("3900.00"), 0.94),
            ("Travis Gallagher", "travis.g@example.com", 5, Decimal("1600.00"), 0.76),
            ("Lauren Montgomery", "lauren.m@example.com", 7, Decimal("2800.00"), 0.84),
            ("Dominic Thorne", "dominic.thorne@example.com", 6, Decimal("2100.00"), 0.80),
        ]

        for name, email, ret_cnt, ltv, risk in high_risk_names:
            c, _ = Customer.objects.update_or_create(
                email=email,
                defaults={
                    "name": name,
                    "return_count": ret_cnt,
                    "lifetime_value": ltv,
                    "risk_score": risk,
                },
            )
            customers.append(c)

        # Medium risk (20 customers)
        for i in range(20):
            c_name = fake.name()
            c_email = f"user.med.{i}_{fake.user_name()}@{fake.free_email_domain()}"
            ret_cnt = random.randint(2, 4)
            ltv = Decimal(str(round(random.uniform(400, 2500), 2)))
            risk = round(random.uniform(0.35, 0.65), 2)
            c, _ = Customer.objects.update_or_create(
                email=c_email,
                defaults={
                    "name": c_name,
                    "return_count": ret_cnt,
                    "lifetime_value": ltv,
                    "risk_score": risk,
                },
            )
            customers.append(c)

        # Low risk (70 customers)
        for i in range(70):
            c_name = fake.name()
            c_email = f"user.low.{i}_{fake.user_name()}@{fake.free_email_domain()}"
            ret_cnt = random.choice([0, 0, 0, 1, 1])
            ltv = Decimal(str(round(random.uniform(80, 1800), 2)))
            risk = round(random.uniform(0.02, 0.22), 2)
            c, _ = Customer.objects.update_or_create(
                email=c_email,
                defaults={
                    "name": c_name,
                    "return_count": ret_cnt,
                    "lifetime_value": ltv,
                    "risk_score": risk,
                },
            )
            customers.append(c)

        # 4. 200 Orders
        self.stdout.write("Creating 200 orders...")
        orders = []
        now = timezone.now()

        for i in range(1, 201):
            order_id = f"ORD-2024-{i:04d}"
            customer = random.choice(customers)
            days_ago = random.randint(5, 60)
            order_date = now - timezone.timedelta(days=days_ago)

            # 90% delivered, 5% shipped, 3% pending, 2% cancelled
            roll = random.random()
            if roll < 0.90:
                status = Order.Status.DELIVERED
                delivered_date = order_date + timezone.timedelta(days=random.randint(2, 4))
            elif roll < 0.95:
                status = Order.Status.SHIPPED
                delivered_date = None
            elif roll < 0.98:
                status = Order.Status.PENDING
                delivered_date = None
            else:
                status = Order.Status.CANCELLED
                delivered_date = None

            order, _ = Order.objects.update_or_create(
                order_id=order_id,
                defaults={
                    "customer": customer,
                    "total": Decimal("0.00"),
                    "status": status,
                    "order_date": order_date,
                    "delivered_date": delivered_date,
                },
            )

            # Add 1-4 items
            item_count = random.randint(1, 4)
            chosen_products = random.sample(products, item_count)
            order_total = Decimal("0.00")

            # Remove previous items if re-seeding
            order.items.all().delete()

            for prod in chosen_products:
                qty = random.randint(1, 2)
                unit_price = prod.price
                OrderItem.objects.create(
                    order=order,
                    product=prod,
                    quantity=qty,
                    unit_price=unit_price,
                )
                order_total += unit_price * qty

            order.total = order_total
            order.save()
            orders.append(order)

        # 5. 30 Return Requests
        self.stdout.write("Creating 30 return requests...")
        # Get delivered orders to create returns from
        delivered_orders = [o for o in orders if o.status == Order.Status.DELIVERED]
        random.shuffle(delivered_orders)

        sample_reasons = [
            ("sizing", "The shirt was too tight around the chest. I need a size Large instead.", "SHIRT-BLU-L"),
            ("sizing", "The jeans were way too long and loose on the waist.", "JEANS-SLM-30"),
            ("defective", "The left earbud makes a loud buzzing sound and won't charge in the case.", None),
            ("defective", "The electric kettle stopped heating water on the 3rd day of use.", None),
            ("changed_mind", "Decided to keep my old headphones instead. Item is completely unopened.", None),
            ("changed_mind", "Bought this as a gift for someone but they already had one.", None),
            ("wrong_item", "Ordered white Oxford shirt but received blue shirt instead.", "SHIRT-WHT-M"),
            ("wrong_item", "Received size 34 instead of size 32 denim.", "JEANS-SLM-32"),
            ("not_as_described", "The backpack color is much darker than shown in the website photos.", None),
            ("not_as_described", "The fabric is 60% polyester, but the listing stated 100% organic cotton.", None),
            ("other", "Delivery box was crushed during transit, compromising inner components.", None),
        ]

        # 30 Returns distribution:
        # 8 pending, 6 awaiting_approval, 8 approved, 4 rejected, 4 exchanged
        statuses_plan = (
            [ReturnRequest.Status.PENDING] * 8
            + [ReturnRequest.Status.AWAITING_APPROVAL] * 6
            + [ReturnRequest.Status.APPROVED] * 8
            + [ReturnRequest.Status.REJECTED] * 4
            + [ReturnRequest.Status.EXCHANGED] * 4
        )

        return_requests = []
        for idx, target_status in enumerate(statuses_plan, start=1):
            return_id = f"RET-2024-{idx:04d}"
            order = delivered_orders[idx - 1]
            order_items = list(order.items.all())
            selected_items = random.sample(order_items, min(len(order_items), random.randint(1, 2)))

            reason_classified, reason_text, exchange_sku = random.choice(sample_reasons)
            refund_amt = sum(item.unit_price * item.quantity for item in selected_items)

            risk_flags = []
            if order.customer.risk_score > 0.7:
                risk_flags.append(f"High risk customer (score: {order.customer.risk_score:.2f})")
                risk_flags.append(f"Customer has {order.customer.return_count} prior returns")
            if refund_amt > 100:
                risk_flags.append(f"High value refund (${refund_amt:.2f} > $100.00)")

            exchange_rec = ""
            if exchange_sku:
                exchange_rec = f"Recommended exchange: SKU {exchange_sku} based on customer sizing feedback."

            resolved_at = None
            if target_status in [ReturnRequest.Status.APPROVED, ReturnRequest.Status.REJECTED, ReturnRequest.Status.EXCHANGED]:
                resolved_at = order.order_date + timezone.timedelta(days=random.randint(5, 15))

            ret_req, _ = ReturnRequest.objects.update_or_create(
                return_id=return_id,
                defaults={
                    "order": order,
                    "reason_text": reason_text,
                    "reason_classified": reason_classified,
                    "status": target_status,
                    "refund_amount": refund_amt,
                    "exchange_recommendation": exchange_rec,
                    "risk_flags": risk_flags,
                    "resolved_at": resolved_at,
                },
            )
            ret_req.items.set(selected_items)
            return_requests.append(ret_req)

        # 6. 10 Refund Ledgers for resolved returns
        self.stdout.write("Creating 10 refund ledger entries...")
        resolved_returns = [r for r in return_requests if r.status in [ReturnRequest.Status.APPROVED, ReturnRequest.Status.REJECTED]]
        for ret in resolved_returns[:10]:
            is_approved = ret.status == ReturnRequest.Status.APPROVED
            decision = RefundLedger.Decision.APPROVED if is_approved else RefundLedger.Decision.REJECTED
            amount = ret.refund_amount if is_approved else Decimal("0.00")
            method = random.choice(["original_payment", "store_credit"]) if is_approved else "original_payment"
            decided_by = "agent" if random.random() < 0.6 else "admin@returnpilot.io"
            reason = "Automated policy approval" if is_approved else "Violates return policy window / condition"

            RefundLedger.objects.update_or_create(
                return_request=ret,
                defaults={
                    "amount": amount,
                    "method": method,
                    "decision": decision,
                    "decided_by": decided_by,
                    "reason": reason,
                },
            )

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
        self.stdout.write(f"  • Policies: {ReturnPolicy.objects.count()}")
        self.stdout.write(f"  • Products: {Product.objects.count()}")
        self.stdout.write(f"  • Customers: {Customer.objects.count()}")
        self.stdout.write(f"  • Orders: {Order.objects.count()}")
        self.stdout.write(f"  • Return Requests: {ReturnRequest.objects.count()}")
        self.stdout.write(f"  • Refund Ledgers: {RefundLedger.objects.count()}")
