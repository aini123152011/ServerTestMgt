from celery import Celery

from app.core.config import settings

celery_app = Celery("servertestlab", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=86400,
    task_time_limit=90000,
    result_expires=604800,
    broker_transport_options={"visibility_timeout": 90000},
    beat_schedule={},
    imports=["app.workers.test_tasks", "app.workers.bmc_tasks"],
)
