from pydantic import BaseModel



class ProgramInfo(BaseModel):
    title: str
    description: str
    season: str | None = None
    year: int | None = None
    age_group: str | None = None
    gender: str | None = None
    url: str | None = None

class InterestsData(BaseModel):
    interests: list[str]

class Programs(BaseModel):
    programs: list[ProgramInfo]