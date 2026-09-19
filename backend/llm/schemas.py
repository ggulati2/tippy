"""The exact JSON shapes we ask the LLM for. Anything else is rejected."""
from pydantic import BaseModel, Field


class WordsReply(BaseModel):
    words: list[str] = Field(min_length=1, max_length=60)


class SentencesReply(BaseModel):
    sentences: list[str] = Field(min_length=1, max_length=40)


class MascotReply(BaseModel):
    lines: list[str] = Field(min_length=1, max_length=30)


SCHEMAS = {"words": (WordsReply, "words"), "sentences": (SentencesReply, "sentences"), "mascot": (MascotReply, "lines")}
