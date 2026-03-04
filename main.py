from fastapi import FastAPI
from api.webhook_handler import router as webhook_router
from db import pool, get_conn

app = FastAPI()

# 2. This 'mounts' your webhook logic. 
# All routes in webhooks.py will now start with /api/v1/webhooks
app.include_router(webhook_router, prefix="/api/v1/webhooks", tags=["Webhooks"])

@app.on_event("startup")
async def startup():
    await pool.open()

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

