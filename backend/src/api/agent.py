"""轻量 Agent API：舆情问答 / 简报。"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.lib.http import err, ok
from src.services.agent import (
    AgentUnavailableError,
    agent_brief,
    agent_chat,
    agent_status,
)

router = APIRouter(tags=["agent"])


class ChatTurn(BaseModel):
    role: str
    content: str = Field(max_length=2000)


class AgentChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=6)


@router.get("/agent/status")
def get_agent_status():
    return ok(agent_status())


@router.post("/agent/chat")
def post_agent_chat(body: AgentChatIn):
    try:
        history = [t.model_dump() for t in body.history]
        data = agent_chat(body.question, history=history)
        return ok(data)
    except ValueError as exc:
        return err("invalid_question", str(exc), status=400)
    except AgentUnavailableError as exc:
        return err("agent_unavailable", str(exc), status=503)
    except Exception as exc:
        return err("agent_failed", f"问答失败: {exc}", status=500)


@router.post("/agent/brief")
def post_agent_brief():
    try:
        data = agent_brief()
        return ok(data)
    except AgentUnavailableError as exc:
        return err("agent_unavailable", str(exc), status=503)
    except Exception as exc:
        return err("agent_failed", f"简报生成失败: {exc}", status=500)
