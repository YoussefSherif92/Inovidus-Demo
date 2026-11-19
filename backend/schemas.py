from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    text: str = Field(min_length=1, max_length=3000)
    limit: int = Field(default=3, ge=1, le=5)


class EmailRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=6000)


class DamageEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ongoing_leak: str | None
    property_damage: str | None
    photos: str | None


class DamageReport(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )

    tenant_name: str | None
    address: str | None
    unit_description: str | None

    damage_type: Literal[
        "water_damage",
        "blocked_drain",
        "heating_failure",
        "mould",
        "other",
        "unknown",
    ]

    damage_summary: str

    ongoing_leak: bool | None
    property_damage_reported: bool | None
    photos_mentioned: bool | None

    evidence: DamageEvidence