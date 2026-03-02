from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi import HTTPException, status
from services.ai_service import process_email
from schemas.postmark import PostmarkInbound
from api.deps import verify_credentials

router = APIRouter()

@router.post("/inbound")
async def handle_sendgrid_webhook(
    data: PostmarkInbound,
    background_tasks: BackgroundTasks,
    _: str = Depends(verify_credentials),
):
    # 1. We acknowledge receipt immediately
    # 2. We trigger the AI logic in the background
    background_tasks.add_task(process_email, 
                              data.from_email, 
                              data.subject, 
                              data.text_body, 
                              data.message_id, 
                              data.raw_email)
    return {"status": "accepted"}

@router.get("/status")
async def get_status():
    return {
        "status": "online",
        "hardware": "Raspberry Pi 5",
        "message": "FastAPI is running behind Caddy!"
    }