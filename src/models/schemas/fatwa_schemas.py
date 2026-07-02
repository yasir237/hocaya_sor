"""
API request/response Pydantic şemaları.
"""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000, description="Kullanıcının sorusu")
    top_k: int = Field(default=5, ge=1, le=10, description="Kaç fetva getirilsin (1-10)")


class FatwaSource(BaseModel):
    id: str
    question: str
    answer: str
    main_category: str
    source_dataset: str
    source_url: str | None = None


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[FatwaSource]