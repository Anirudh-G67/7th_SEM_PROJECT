from pydantic import BaseModel, Field


class InterviewRequest(BaseModel):
    education: str = Field(min_length=1)
    experience: int = Field(ge=0)
    interview_type: str = Field(min_length=1)
    target_role: str = Field(min_length=1)
    interview_difficulty: str = Field(min_length=1)
    interview_length: int = Field(ge=1, le=100)


class AnswerRequest(BaseModel):
    # Empty answers are allowed so they can be scored as Unattempted.
    answer: str = ""
