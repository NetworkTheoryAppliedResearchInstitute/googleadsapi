from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AdStatus(str, Enum):
    ENABLED = "ENABLED"
    PAUSED = "PAUSED"
    REMOVED = "REMOVED"


class PinnedField(str, Enum):
    HEADLINE_1 = "HEADLINE_1"
    HEADLINE_2 = "HEADLINE_2"
    HEADLINE_3 = "HEADLINE_3"
    DESCRIPTION_1 = "DESCRIPTION_1"
    DESCRIPTION_2 = "DESCRIPTION_2"


class AdTextAsset(BaseModel):
    text: str = Field(..., min_length=1)
    pinned_field: Optional[PinnedField] = None


class CreateRSARequest(BaseModel):
    ad_group_id: str

    # RSA requires 3–15 headlines and 2–4 descriptions
    headlines: list[AdTextAsset] = Field(..., min_length=3, max_length=15)
    descriptions: list[AdTextAsset] = Field(..., min_length=2, max_length=4)

    # Display URL path components (each max 15 chars)
    path1: Optional[str] = Field(None, max_length=15)
    path2: Optional[str] = Field(None, max_length=15)

    final_urls: list[str] = Field(..., min_length=1, description="At least one final URL.")
    final_mobile_urls: list[str] = Field(default_factory=list)

    status: AdStatus = AdStatus.PAUSED

    # Ad customizer — attribute name used in {CUSTOMIZER.AttributeName:DefaultValue}
    # Leave empty if not using customizers
    customizer_attribute_name: Optional[str] = None
    customizer_default_value: Optional[str] = None

    @field_validator("headlines")
    @classmethod
    def validate_headline_lengths(cls, headlines: list[AdTextAsset]) -> list[AdTextAsset]:
        for h in headlines:
            if len(h.text) > 30:
                raise ValueError(
                    f"Headline '{h.text[:20]}…' exceeds 30-character limit."
                )
        return headlines

    @field_validator("descriptions")
    @classmethod
    def validate_description_lengths(
        cls, descriptions: list[AdTextAsset]
    ) -> list[AdTextAsset]:
        for d in descriptions:
            if len(d.text) > 90:
                raise ValueError(
                    f"Description '{d.text[:20]}…' exceeds 90-character limit."
                )
        return descriptions


class UpdateRSARequest(BaseModel):
    status: Optional[AdStatus] = None
    headlines: Optional[list[AdTextAsset]] = Field(None, max_length=15)
    descriptions: Optional[list[AdTextAsset]] = Field(None, max_length=4)
    final_urls: Optional[list[str]] = None
    path1: Optional[str] = Field(None, max_length=15)
    path2: Optional[str] = Field(None, max_length=15)


class RSAResponse(BaseModel):
    resource_name: str
    ad_id: str
    ad_group_id: str
    status: str
    headlines: list[dict]
    descriptions: list[dict]
    final_urls: list[str]
    path1: Optional[str] = None
    path2: Optional[str] = None


class CampaignLevelAdAssets(BaseModel):
    """Campaign-level headlines and descriptions (up to 3 headlines, 2 descriptions)."""
    campaign_id: str
    headlines: list[AdTextAsset] = Field(..., max_length=3)
    descriptions: list[AdTextAsset] = Field(..., max_length=2)
