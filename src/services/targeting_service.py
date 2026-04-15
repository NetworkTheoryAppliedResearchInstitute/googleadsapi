"""Full targeting management — geo, language, demographics, devices, schedules, audiences."""

from __future__ import annotations

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from src.auth.client import normalize_customer_id
from src.models.targeting import (
    GeoTargetRequest,
    GeoTargetPolarity,
    LanguageTargetRequest,
    DemographicTargetRequest,
    DeviceTargetRequest,
    AdScheduleRequest,
    AudienceTargetRequest,
)
from src.utils.error_handling import handle_google_ads_exception


class TargetingService:
    def __init__(self, client: GoogleAdsClient) -> None:
        self.client = client

    # ── Geo targeting ─────────────────────────────────────────────────────────

    def add_geo_target(self, customer_id: str, req: GeoTargetRequest) -> dict:
        customer_id = normalize_customer_id(customer_id)

        if req.campaign_id:
            svc = self.client.get_service("CampaignCriterionService")
            op = self.client.get_type("CampaignCriterionOperation")
            criterion = op.create
            campaign_svc = self.client.get_service("CampaignService")
            criterion.campaign = campaign_svc.campaign_path(
                customer_id, req.campaign_id
            )
            criterion.negative = req.polarity == GeoTargetPolarity.NEGATIVE
            gtc_svc = self.client.get_service("GeoTargetConstantService")
            criterion.location.geo_target_constant = (
                gtc_svc.geo_target_constant_path(req.geo_target_constant_id)
            )
            if req.bid_modifier is not None:
                criterion.bid_modifier = req.bid_modifier
            try:
                resp = svc.mutate_campaign_criteria(
                    customer_id=customer_id, operations=[op]
                )
            except GoogleAdsException as exc:
                handle_google_ads_exception(exc)
            return {"resource_name": resp.results[0].resource_name}

        elif req.ad_group_id:
            svc = self.client.get_service("AdGroupCriterionService")
            op = self.client.get_type("AdGroupCriterionOperation")
            criterion = op.create
            ag_svc = self.client.get_service("AdGroupService")
            criterion.ad_group = ag_svc.ad_group_path(
                customer_id, req.ad_group_id
            )
            criterion.negative = req.polarity == GeoTargetPolarity.NEGATIVE
            gtc_svc = self.client.get_service("GeoTargetConstantService")
            criterion.location.geo_target_constant = (
                gtc_svc.geo_target_constant_path(req.geo_target_constant_id)
            )
            try:
                resp = svc.mutate_ad_group_criteria(
                    customer_id=customer_id, operations=[op]
                )
            except GoogleAdsException as exc:
                handle_google_ads_exception(exc)
            return {"resource_name": resp.results[0].resource_name}

        raise ValueError("Provide either campaign_id or ad_group_id.")

    # ── Language targeting ────────────────────────────────────────────────────

    def add_language_target(self, customer_id: str, req: LanguageTargetRequest) -> dict:
        customer_id = normalize_customer_id(customer_id)
        svc = self.client.get_service("CampaignCriterionService")
        op = self.client.get_type("CampaignCriterionOperation")
        criterion = op.create
        campaign_svc = self.client.get_service("CampaignService")
        criterion.campaign = campaign_svc.campaign_path(customer_id, req.campaign_id)
        lc_svc = self.client.get_service("LanguageConstantService")
        criterion.language.language_constant = lc_svc.language_constant_path(
            req.language_constant_id
        )
        try:
            resp = svc.mutate_campaign_criteria(
                customer_id=customer_id, operations=[op]
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)
        return {"resource_name": resp.results[0].resource_name}

    # ── Demographic targeting ─────────────────────────────────────────────────

    def add_demographic_targets(
        self, customer_id: str, req: DemographicTargetRequest
    ) -> dict:
        customer_id = normalize_customer_id(customer_id)
        svc = self.client.get_service("AdGroupCriterionService")
        ops = []

        ag_svc = self.client.get_service("AdGroupService")
        ag_path = ag_svc.ad_group_path(customer_id, req.ad_group_id)

        for age in req.age_ranges:
            op = self.client.get_type("AdGroupCriterionOperation")
            c = op.create
            c.ad_group = ag_path
            c.negative = req.negative
            c.age_range.type_ = self.client.enums.AgeRangeTypeEnum[age.value]
            ops.append(op)

        for gender in req.genders:
            op = self.client.get_type("AdGroupCriterionOperation")
            c = op.create
            c.ad_group = ag_path
            c.negative = req.negative
            c.gender.type_ = self.client.enums.GenderTypeEnum[gender.value]
            ops.append(op)

        for status in req.parental_statuses:
            op = self.client.get_type("AdGroupCriterionOperation")
            c = op.create
            c.ad_group = ag_path
            c.negative = req.negative
            c.parental_status.type_ = self.client.enums.ParentalStatusTypeEnum[
                status.value
            ]
            ops.append(op)

        for income in req.household_incomes:
            op = self.client.get_type("AdGroupCriterionOperation")
            c = op.create
            c.ad_group = ag_path
            c.negative = req.negative
            c.income_range.type_ = self.client.enums.IncomeRangeTypeEnum[income.value]
            ops.append(op)

        if not ops:
            return {"created": 0}

        try:
            resp = svc.mutate_ad_group_criteria(
                customer_id=customer_id, operations=ops
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)

        return {"created": len(resp.results)}

    # ── Device targeting ──────────────────────────────────────────────────────

    def set_device_bid_modifier(
        self, customer_id: str, req: DeviceTargetRequest
    ) -> dict:
        customer_id = normalize_customer_id(customer_id)
        svc = self.client.get_service("CampaignCriterionService")
        op = self.client.get_type("CampaignCriterionOperation")
        criterion = op.create
        campaign_svc = self.client.get_service("CampaignService")
        criterion.campaign = campaign_svc.campaign_path(customer_id, req.campaign_id)
        criterion.device.type_ = self.client.enums.DeviceEnum[req.device.value]
        criterion.bid_modifier = req.bid_modifier
        try:
            resp = svc.mutate_campaign_criteria(
                customer_id=customer_id, operations=[op]
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)
        return {"resource_name": resp.results[0].resource_name}

    # ── Ad schedule targeting ─────────────────────────────────────────────────

    def add_ad_schedule(self, customer_id: str, req: AdScheduleRequest) -> dict:
        customer_id = normalize_customer_id(customer_id)
        svc = self.client.get_service("CampaignCriterionService")
        op = self.client.get_type("CampaignCriterionOperation")
        criterion = op.create
        campaign_svc = self.client.get_service("CampaignService")
        criterion.campaign = campaign_svc.campaign_path(customer_id, req.campaign_id)
        criterion.bid_modifier = req.bid_modifier

        schedule = criterion.ad_schedule
        schedule.day_of_week = self.client.enums.DayOfWeekEnum[req.day_of_week.value]
        schedule.start_hour = req.start_hour
        schedule.start_minute = self.client.enums.MinuteOfHourEnum[
            f"ZERO" if req.start_minute == 0
            else f"FIFTEEN" if req.start_minute == 15
            else f"THIRTY" if req.start_minute == 30
            else "FORTY_FIVE"
        ]
        schedule.end_hour = req.end_hour
        schedule.end_minute = self.client.enums.MinuteOfHourEnum[
            f"ZERO" if req.end_minute == 0
            else f"FIFTEEN" if req.end_minute == 15
            else f"THIRTY" if req.end_minute == 30
            else "FORTY_FIVE"
        ]
        try:
            resp = svc.mutate_campaign_criteria(
                customer_id=customer_id, operations=[op]
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)
        return {"resource_name": resp.results[0].resource_name}

    # ── Audience targeting ────────────────────────────────────────────────────

    def add_audience_target(
        self, customer_id: str, req: AudienceTargetRequest
    ) -> dict:
        customer_id = normalize_customer_id(customer_id)
        svc = self.client.get_service("AdGroupCriterionService")
        op = self.client.get_type("AdGroupCriterionOperation")
        criterion = op.create
        ag_svc = self.client.get_service("AdGroupService")
        criterion.ad_group = ag_svc.ad_group_path(customer_id, req.ad_group_id)
        criterion.negative = req.negative

        from src.models.targeting import AudienceTargetType
        t = req.audience_type
        if t == AudienceTargetType.USER_LIST:
            criterion.user_list.user_list = req.criterion_resource_name
        elif t in (AudienceTargetType.IN_MARKET, AudienceTargetType.AFFINITY):
            criterion.user_interest.user_interest_category = (
                req.criterion_resource_name
            )
        elif t == AudienceTargetType.LIFE_EVENT:
            criterion.life_event.life_event = req.criterion_resource_name
        else:
            # Custom intent, similar audiences, customer match all use user_list
            criterion.user_list.user_list = req.criterion_resource_name

        if req.bid_modifier is not None:
            criterion.bid_modifier = req.bid_modifier

        try:
            resp = svc.mutate_ad_group_criteria(
                customer_id=customer_id, operations=[op]
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)
        return {"resource_name": resp.results[0].resource_name}
