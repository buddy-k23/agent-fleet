"""Chat API — WebSocket endpoint for agent conversations."""

import json

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from agent_fleet.api.deps import get_supabase_client

logger = structlog.get_logger()
router = APIRouter(tags=["chat"])


@router.websocket("/ws/chat/{conversation_id}")
async def chat_ws(websocket: WebSocket, conversation_id: str) -> None:
    """WebSocket for real-time chat with an agent."""
    await websocket.accept()
    logger.info("chat_ws_connected", conversation_id=conversation_id)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            user_content = msg.get("content", "")
            agent_name = msg.get("agent", "architect")

            # Save user message to Supabase
            client = get_supabase_client()
            if client:
                client.table("messages").insert(
                    {
                        "conversation_id": conversation_id,
                        "role": "user",
                        "content": user_content,
                    }
                ).execute()

            # Send thinking indicator
            await websocket.send_json({"type": "thinking"})

            # For now, echo back a simulated response
            # TODO: Wire to AgentRunner with LLM + tools
            response = (
                f"I'm the {agent_name} agent. You said: {user_content}\n\n"
                "Real LLM responses will be streamed here once wired to AgentRunner."
            )

            # Stream tokens (simulated)
            words = response.split(" ")
            for i, word in enumerate(words):
                await websocket.send_json(
                    {
                        "type": "token",
                        "content": word + " ",
                    }
                )

            # Save assistant message
            if client:
                client.table("messages").insert(
                    {
                        "conversation_id": conversation_id,
                        "role": "assistant",
                        "content": response,
                        "metadata": {"agent": agent_name, "tokens_used": 0},
                    }
                ).execute()

            # Done
            await websocket.send_json(
                {
                    "type": "done",
                    "content": response,
                    "tokens_used": 0,
                }
            )

    except WebSocketDisconnect:
        logger.info("chat_ws_disconnected", conversation_id=conversation_id)
    except Exception as e:
        logger.error("chat_ws_error", error=str(e))
