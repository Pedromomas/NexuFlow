from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


BoostProfile = Literal["ping", "pc", "complete", "hardcore_safe"]


class BoostRequest(BaseModel):
    profile: BoostProfile = "complete"


class RouteBenchmarkRequest(BaseModel):
    ips: list[str] = Field(min_length=2, max_length=64)
    attempts: int = Field(default=4, ge=2, le=10)


class RouteApplyRequest(RouteBenchmarkRequest):
    game_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    program: str = Field(min_length=3, max_length=1024)
    interchangeable: bool = False
    confirmed: bool = False
    keep_best: int = Field(default=1, ge=1, le=4)


class FlushRequest(BaseModel):
    confirm_disconnect: bool = False
    include_ip_reset: bool = False


class ProcessPriorityRequest(BaseModel):
    pid: int = Field(gt=0)
    aggressive: bool = False
