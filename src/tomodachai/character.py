from __future__ import annotations

from pydantic import BaseModel


class Character(BaseModel):
    id: str
    name: str
    personality_code: str
    speech_habit: str = ""
    backstory: str = ""
