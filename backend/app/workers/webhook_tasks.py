"""Webhook callback tasks for CI/CD integration."""

from __future__ import annotations

import logging

import httpx

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="webhook_tasks.send_webhook_callback", max_retries=3)
def send_webhook_callback(self, callback_url: str, payload: dict):
    """POST job completion data to the CI/CD callback URL."""
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(callback_url, json=payload)
            resp.raise_for_status()
            logger.info(f"Webhook callback sent to {callback_url}: {resp.status_code}")
    except Exception as exc:
        logger.warning(f"Webhook callback to {callback_url} failed: {exc}, retrying...")
        raise self.retry(exc=exc, countdown=10 * (self.request.retries + 1))
