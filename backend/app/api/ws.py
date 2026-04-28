"""WebSocket endpoint for real-time job status and log streaming."""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.websocket import ws_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/jobs/{job_id}")
async def job_ws(websocket: WebSocket, job_id: int):
    channel = f"job:{job_id}:status"
    await ws_manager.connect(websocket, channel)

    # Start Redis subscription relay in background
    sub_task = asyncio.create_task(ws_manager.subscribe_loop(channel))

    try:
        # Keep connection alive; read client messages (ping/pong or ignore)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.debug(f"WebSocket closed for job {job_id}")
    finally:
        ws_manager.disconnect(websocket, channel)
        sub_task.cancel()
        try:
            await sub_task
        except asyncio.CancelledError:
            pass
