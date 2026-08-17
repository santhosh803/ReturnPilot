import json
import logging
import os
from decimal import Decimal
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .models import ReturnRequest, Product, Customer

logger = logging.getLogger(__name__)


def _get_vertex_llm(model_name: str = "gemini-2.5-flash", temperature: float = 0.2):
    try:
        from langchain_google_vertexai import ChatVertexAI

        return ChatVertexAI(
            model_name=model_name,
            project=getattr(settings, "GOOGLE_CLOUD_PROJECT", "ai-projects-500402"),
            location=getattr(settings, "GOOGLE_CLOUD_LOCATION", "us-central1"),
            temperature=temperature,
        )
    except Exception as e:
        logger.warning(f"Could not initialize ChatVertexAI: {e}")
        return None


@shared_task(name="core.tasks.classify_return_reason_task")
def classify_return_reason_task(return_request_id: int):
    """
    Celery task to classify customer return reason using Gemini (Vertex AI).
    Updates ReturnRequest.reason_classified and evaluates customer risk score.
    """
    try:
        return_request = ReturnRequest.objects.select_related("order__customer").get(
            id=return_request_id
        )
    except ReturnRequest.DoesNotExist:
        logger.error(f"ReturnRequest id {return_request_id} does not exist.")
        return {"error": f"ReturnRequest {return_request_id} not found"}

    reason_text = return_request.reason_text or ""
    classification = "other"
    confidence = 0.85
    dist = {}

    llm = _get_vertex_llm()
    if llm and reason_text:
        prompt = (
            "You are a return reason classifier for an eCommerce platform. "
            "Classify the customer's return reason into exactly one of the following valid categories: "
            "sizing, defective, changed_mind, wrong_item, not_as_described, other.\n\n"
            f"Customer Reason: \"{reason_text}\"\n\n"
            "Respond ONLY with valid JSON in this exact structure without markdown backticks:\n"
            "{\"classification\": \"sizing\", \"confidence\": 0.95, \"category_distribution\": {\"sizing\": 0.95, \"not_as_described\": 0.03, \"other\": 0.02}}"
        )
        try:
            response = llm.invoke(prompt)
            content = response.content.strip()
            # Clean markdown codeblocks if returned
            if content.startswith("```"):
                lines = content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()

            parsed = json.loads(content)
            classification = parsed.get("classification", "other").lower()
            confidence = float(parsed.get("confidence", 0.90))
            dist = parsed.get("category_distribution", {})
        except Exception as e:
            logger.warning(f"Gemini classification call failed: {e}. Using rule-based fallback.")
            llm = None

    if not llm or classification not in dict(ReturnRequest.Reason.choices):
        # Heuristic fallback
        reason_lower = reason_text.lower()
        if any(w in reason_lower for w in ["fit", "small", "large", "size", "tight", "loose", "length"]):
            classification = "sizing"
            confidence = 0.94
        elif any(w in reason_lower for w in ["broken", "screen", "stopped", "defective", "damage", "faulty", "buzzing", "dead"]):
            classification = "defective"
            confidence = 0.96
        elif any(w in reason_lower for w in ["wrong", "received", "instead", "sent"]):
            classification = "wrong_item"
            confidence = 0.92
        elif any(w in reason_lower for w in ["different", "photo", "picture", "color", "material", "described", "fake", "quality"]):
            classification = "not_as_described"
            confidence = 0.91
        elif any(w in reason_lower for w in ["mind", "decided", "gift", "keep", "bought", "accidental", "duplicate"]):
            classification = "changed_mind"
            confidence = 0.95
        else:
            classification = "other"
            confidence = 0.70
        dist = {classification: confidence, "other": round(1.0 - confidence, 2)}

    return_request.reason_classified = classification
    return_request.save()

    # Update customer return metrics and risk score
    customer = return_request.order.customer
    all_customer_returns = ReturnRequest.objects.filter(order__customer=customer)
    total_returns = all_customer_returns.count()
    customer.return_count = total_returns

    # Dynamic risk calculation
    total_orders = customer.orders.count()
    return_ratio = (total_returns / total_orders) if total_orders > 0 else 0.5
    base_risk = min(1.0, return_ratio * 0.8 + (0.1 if total_returns > 3 else 0.0))
    customer.risk_score = round(base_risk, 2)
    customer.save()

    logger.info(
        f"[AI TASK] Classified return {return_request.return_id} as '{classification}' (confidence: {confidence:.2f})"
    )

    # Chain to exchange recommendation
    generate_exchange_recommendation_task.delay(return_request.id)

    return {
        "return_id": return_request.return_id,
        "classification": classification,
        "confidence": confidence,
        "distribution": dist,
    }


@shared_task(name="core.tasks.generate_exchange_recommendation_task")
def generate_exchange_recommendation_task(return_request_id: int):
    """
    Celery task to generate AI-powered exchange recommendations based on return reason and catalog.
    """
    try:
        return_request = (
            ReturnRequest.objects.select_related("order")
            .prefetch_related("items__product")
            .get(id=return_request_id)
        )
    except ReturnRequest.DoesNotExist:
        logger.error(f"ReturnRequest id {return_request_id} does not exist.")
        return {"error": f"ReturnRequest {return_request_id} not found"}

    first_item = return_request.items.first()
    if not first_item:
        return {"message": "No items attached to return request"}

    product = first_item.product
    category = product.category
    reason = return_request.reason_classified or "sizing"

    catalog_alternatives = list(
        Product.objects.filter(category__iexact=category)
        .exclude(sku=product.sku)
        .values("sku", "name", "price", "inventory_count", "description")[:6]
    )

    llm = _get_vertex_llm()
    recommendation_text = ""

    if llm and catalog_alternatives:
        prompt = (
            "You are an eCommerce exchange recommendation engine. "
            "Based on the customer's return reason and the original purchased item, select up to 3 best exchange alternatives from the catalog list below.\n\n"
            f"Original Product: {product.name} (SKU: {product.sku}, Price: ${product.price})\n"
            f"Customer Return Reason: {return_request.reason_text} (Classified as: {reason})\n\n"
            f"Available Catalog Items:\n{json.dumps(catalog_alternatives, default=str)}\n\n"
            "Respond ONLY with valid JSON in this exact structure without markdown backticks:\n"
            "{\"recommendations\": [{\"sku\": \"...\", \"name\": \"...\", \"reason\": \"...\"}], \"exchange_incentive\": \"Free shipping on exchange + 10% store credit\"}"
        )
        try:
            response = llm.invoke(prompt)
            content = response.content.strip()
            if content.startswith("```"):
                lines = content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()

            parsed = json.loads(content)
            recs = parsed.get("recommendations", [])
            incentive = parsed.get("exchange_incentive", "Free shipping on exchange")
            rec_lines = [f"• {r.get('name')} ({r.get('sku')}): {r.get('reason')}" for r in recs]
            recommendation_text = (
                "AI Exchange Recommendations:\n"
                + "\n".join(rec_lines)
                + f"\n\nIncentive: {incentive}"
            )
        except Exception as e:
            logger.warning(f"Gemini exchange recommendation failed: {e}. Using catalog fallback.")
            llm = None

    if not recommendation_text:
        # Fallback catalog suggestions
        fallback_recs = catalog_alternatives[:3]
        rec_lines = [
            f"• {item['name']} (SKU: {item['sku']}, ${item['price']}) — Catalog match for {category}"
            for item in fallback_recs
        ]
        recommendation_text = (
            "Recommended Alternatives:\n"
            + "\n".join(rec_lines)
            + "\n\nIncentive: Free express exchange shipping + 10% store credit bonus."
        )

    return_request.exchange_recommendation = recommendation_text
    return_request.save()

    logger.info(
        f"[AI TASK] Generated exchange recommendations for return {return_request.return_id}"
    )

    return {
        "return_id": return_request.return_id,
        "recommendation": recommendation_text,
    }
