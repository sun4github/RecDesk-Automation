from pydantic import BaseModel

class PoliticalEmail(BaseModel):
    is_political: bool
    political_statements: list[str]