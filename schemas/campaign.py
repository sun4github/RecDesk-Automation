from pydantic import BaseModel


class Campaign(BaseModel):
    theme: str
    id: str
