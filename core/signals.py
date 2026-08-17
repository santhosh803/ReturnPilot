import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ReturnRequest

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ReturnRequest)
def handle_return_request_created(sender, instance, created, **kwargs):
    if created:
        logger.info(
            f"[SIGNAL] New ReturnRequest created: {instance.return_id} for Order {instance.order.order_id}"
        )
        # Note: In Phase 4, async Celery tasks for Gemini classification
        # and exchange recommendation will be triggered from here.
