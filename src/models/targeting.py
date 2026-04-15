from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GeoTargetPolarity(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"


class GeoTargetRequest(BaseModel):
    """Add or remove geographic targets on a campaign or ad group."""

    campaign_id: Optional[str] = None
    ad_group_id: Optional[str] = None
    geo_target_constant_id: int = Field(
        ...,
        description=(
            "Google Ads GeoTargetConstant ID. "
            "Use the GeoTargetConstantService or the searchable reference at "
            "developers.google.com/google-ads/api/data/geotargets"
        ),
    )
    polarity: GeoTargetPolarity = GeoTargetPolarity.POSITIVE
    bid_modifier: Optional[float] = Field(
        None, ge=0.1, le=10.0, description="Bid multiplier for this location."
    )


class LanguageTargetRequest(BaseModel):
    campaign_id: str
    language_constant_id: int = Field(
        ...,
        description=(
            "Google Ads LanguageConstant ID. "
            "English = 1000, Spanish = 1003, French = 1002, etc."
        ),
    )


class AgeRange(str, Enum):
    AGE_18_24 = "AGE_RANGE_18_24"
    AGE_25_34 = "AGE_RANGE_25_34"
    AGE_35_44 = "AGE_RANGE_35_44"
    AGE_45_54 = "AGE_RANGE_45_54"
    AGE_55_64 = "AGE_RANGE_55_64"
    AGE_65_UP = "AGE_RANGE_65_UP"
    UNDETERMINED = "AGE_RANGE_UNDETERMINED"


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    UNDETERMINED = "UNDETERMINED"


class ParentalStatus(str, Enum):
    PARENT = "PARENT"
    NOT_A_PARENT = "NOT_A_PARENT"
    UNDETERMINED = "UNDETERMINED"


class HouseholdIncome(str, Enum):
    TOP_10 = "INCOME_RANGE_0_50"
    TOP_11_20 = "INCOME_RANGE_50_60"
    TOP_21_30 = "INCOME_RANGE_60_70"
    TOP_31_40 = "INCOME_RANGE_70_80"
    TOP_41_50 = "INCOME_RANGE_80_90"
    LOWER_50 = "INCOME_RANGE_90_UP"
    UNDETERMINED = "UNDETERMINED"


class DemographicTargetRequest(BaseModel):
    ad_group_id: str
    age_ranges: list[AgeRange] = Field(default_factory=list)
    genders: list[Gender] = Field(default_factory=list)
    parental_statuses: list[ParentalStatus] = Field(default_factory=list)
    household_incomes: list[HouseholdIncome] = Field(default_factory=list)
    # Set to True to exclude (negative) rather than include
    negative: bool = False


class DeviceType(str, Enum):
    DESKTOP = "DESKTOP"
    MOBILE = "MOBILE"
    TABLET = "TABLET"
    CONNECTED_TV = "CONNECTED_TV"


class DeviceTargetRequest(BaseModel):
    campaign_id: str
    device: DeviceType
    bid_modifier: float = Field(
        1.0,
        ge=0.0,
        le=10.0,
        description="0.0 disables the device. 1.0 = no change. 2.0 = double bid.",
    )


class DayOfWeek(str, Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


class AdScheduleRequest(BaseModel):
    campaign_id: str
    day_of_week: DayOfWeek
    start_hour: int = Field(..., ge=0, le=23)
    start_minute: int = Field(0, description="0, 15, 30, or 45.")
    end_hour: int = Field(..., ge=0, le=24)
    end_minute: int = Field(0, description="0, 15, 30, or 45.")
    bid_modifier: float = Field(1.0, ge=0.1, le=10.0)


class AudienceTargetType(str, Enum):
    USER_LIST = "USER_LIST"
    IN_MARKET = "IN_MARKET"
    AFFINITY = "AFFINITY"
    CUSTOM_INTENT = "CUSTOM_INTENT"
    CUSTOMER_MATCH = "CUSTOMER_MATCH"
    SIMILAR_AUDIENCES = "SIMILAR_AUDIENCES"
    LIFE_EVENT = "LIFE_EVENT"


class AudienceTargetRequest(BaseModel):
    ad_group_id: str
    audience_type: AudienceTargetType
    criterion_resource_name: str = Field(
        ...,
        description=(
            "Full resource name of the audience. "
            "e.g. 'customers/123/userLists/456' or "
            "'topics/[topicId]' for in-market/affinity segments."
        ),
    )
    bid_modifier: Optional[float] = Field(None, ge=0.1, le=10.0)
    negative: bool = False
