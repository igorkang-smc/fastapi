from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import jwt_user
from app.models import ChatMessages
from app.llm_func import generate_slack_response
router = APIRouter(tags=["llm"])
@router.post("/chat")
async def llm_response(messages: ChatMessages, token_data: Annotated[dict, Depends(jwt_user)]):
    username = token_data["name"]
    user_input = messages.messages[0].message
    return generate_slack_response(user_input, username)