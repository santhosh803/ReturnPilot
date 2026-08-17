import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ReturnRequest
from .tasks import classify_return_reason_task

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ReturnRequest)
def handle_return_request_created(sender, instance, created, **kwargs):
    if created:
        logger.info(
            f"[SIGNAL] New ReturnRequest created: {instance.return_id} for Order {instance.order.order_id}"
        )
        try:
            classify_return_reason_task.delay(instance.id)
        except Exception as e:
            logger.warning(
                f"[SIGNAL] Celery task dispatch failed ({e}). Running synchronously fallback."
            )
            classify_return_reason_task(instance.id)
