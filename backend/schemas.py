from pydantic import BaseModel, Field, field_validator


class ConceptMap(BaseModel):
    key_ideas: list[str]
    prerequisites: list[str]


class RubricItem(BaseModel):
    text: str
    weight: int = Field(ge=1, le=3)  # 1 = minor, 2 = important, 3 = essential


class TopicBrief(BaseModel):
    title: str
    concept_map: ConceptMap
    misconceptions: list[str]
    rubric: list[RubricItem]

    @field_validator("rubric")
    @classmethod
    def rubric_size(cls, v):
        if not 4 <= len(v) <= 10:
            raise ValueError(f"rubric must have 4 to 10 items, got {len(v)}")
        return v

class TopicCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    notes: str | None = Field(default=None, max_length=20000)


class TopicOut(BaseModel):
    id: int
    title: str
    rubric_count: int
    status: str = "ready"