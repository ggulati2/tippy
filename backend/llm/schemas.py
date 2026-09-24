"""The exact JSON shapes we ask the LLM for. Anything else is rejected."""
from pydantic import BaseModel, Field


class WordsReply(BaseModel):
    words: list[str] = Field(min_length=1, max_length=60)


class SentencesReply(BaseModel):
    sentences: list[str] = Field(min_length=1, max_length=40)


class MascotReply(BaseModel):
    lines: list[str] = Field(min_length=1, max_length=30)


class AskReply(BaseModel):
    answers: list[str] = Field(min_length=1, max_length=10)


class StoryReply(BaseModel):
    stories: list[list[str]] = Field(min_length=1, max_length=10)


class SummaryReply(BaseModel):
    strengths: str = Field(max_length=700)
    practice: str = Field(max_length=700)
    tips: str = Field(max_length=700)


SCHEMAS = {"ask": (AskReply, "answers"), "words": (WordsReply, "words"), "sentences": (SentencesReply, "sentences"), "mascot": (MascotReply, "lines"),
           "story": (StoryReply, "stories")}
