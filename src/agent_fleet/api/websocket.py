"""WebSocket endpoint for real-time task status streaming."""
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = structlog.get_logger()
router = APIRouter()


@router.websocket("/ws/tasks/{task_id}")
async def task_status_ws(websocket: WebSocket, task_id: str) -> None:
    """Stream task status updates via WebSocket."""
    await websocket.accept()
    logger.info("ws_connected", task_id=task_id)
    try:
        # Send initial status
        await websocket.send_json({"task_id": task_id, "status": "connected"})
        # Keep connection open until client disconnects
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("ws_disconnected", task_id=task_id)
