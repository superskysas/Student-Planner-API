from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, constr

AllowedType = Literal["task", "meeting", "deadline", "holiday", "news"]
AllowedStatus = Literal["todo", "done"]


class TaskCreate(BaseModel):
    title: constr(min_length=1, max_length=200)
    date: date
    type: AllowedType = "task"


class TaskUpdate(BaseModel):
    title: Optional[constr(min_length=1, max_length=200)] = None
    date: Optional[date] = None
    type: Optional[AllowedType] = None
    status: Optional[AllowedStatus] = None


class TaskOut(BaseModel):
    id: str
    title: str
    date: date
    type: AllowedType
    status: AllowedStatus
    source: Literal["local", "nager"] = "local"
