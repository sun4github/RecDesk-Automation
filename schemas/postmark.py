from pydantic import BaseModel, Field

class PostmarkInbound(BaseModel):
    from_email: str = Field(..., alias="From")
    subject: str = Field(..., alias="Subject")
    text_body: str = Field(..., alias="TextBody")
    message_id: str = Field(..., alias="MessageID")
    raw_email: str = Field(..., alias="RawEmail")   
