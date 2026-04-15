"""Campaign lifecycle management — create, read, update, remove."""

from __future__ import annotations

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from src.auth.client import normalize_customer_id, resource_name_to_id
from src.models.campaigns import (
    CreateCampaignRequest,
    UpdateCampaignRequest,
    CampaignResponse,
    BiddingStrategyType,
    ImpressionShareLocation,
)
from src.utils.ad_grants_compliance import enforce_ad_grants_campaign
from src.utils.error_handling import handle_google_ads_exception


class CampaignService:
    def __init__(self, client: GoogleAdsClient) -> None:
        self.client = client
        self.campaign_svc = client.get_service("CampaignService")
        self.budget_svc = client.get_service("CampaignBudgetService")

    # ── Budget helpers ────────────────────────────────────────────────────────

    def _create_budget(self, customer_id: str, amount_micros: int) -> str:
        """Create a campaign budget and return its resource name."""
        op = self.client.get_type("CampaignBudgetOperation")
        budget = op.create
        budget.amount_micros = amount_micros
        budget.delivery_method = (
            self.client.enums.BudgetDeliveryMethodEnum.STANDARD
        )
        budget.explicitly_shared = False
        resp = self.budget_svc.mutate_campaign_budgets(
            customer_id=customer_id, operations=[op]
        )
        return resp.results[0].resource_name

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create(
        self, customer_id: str, req: CreateCampaignRequest
    ) -> CampaignResponse:
        customer_id = normalize_customer_id(customer_id)

        if req.ad_grants_account:
            enforce_ad_grants_campaign(req)

        # Budget
        if req.daily_budget_micros:
            budget_rn = self._create_budget(customer_id, req.daily_budget_micros)
        elif req.shared_budget_resource_name:
            budget_rn = req.shared_budget_resource_name
        else:
            raise ValueError(
                "Provide either daily_budget_micros or shared_budget_resource_name."
            )

        op = self.client.get_type("CampaignOperation")
        campaign = op.create

        campaign.name = req.name
        campaign.status = self.client.enums.CampaignStatusEnum[req.status.value]
        campaign.campaign_budget = budget_rn

        # Campaign type / advertising channel
        campaign.advertising_channel_type = (
            self.client.enums.AdvertisingChannelTypeEnum[req.campaign_type.value]
        )

        # Network settings
        ns = campaign.network_settings
        ns.target_google_search = req.network_settings.target_google_search
        ns.target_search_network = req.network_settings.target_search_network
        ns.target_content_network = req.network_settings.target_content_network
        ns.target_partner_search_network = (
            req.network_settings.target_partner_search_network
        )

        # Bidding strategy
        self._apply_bidding(campaign, req)

        # Schedule
        if req.start_date:
            campaign.start_date = req.start_date
        if req.end_date:
            campaign.end_date = req.end_date

        try:
            resp = self.campaign_svc.mutate_campaigns(
                customer_id=customer_id, operations=[op]
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)

        rn = resp.results[0].resource_name
        return CampaignResponse(
            resource_name=rn,
            campaign_id=resource_name_to_id(rn),
            name=req.name,
            status=req.status.value,
            campaign_type=req.campaign_type.value,
            budget_resource_name=budget_rn,
        )

    def get(self, customer_id: str, campaign_id: str) -> dict:
        customer_id = normalize_customer_id(customer_id)
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign.campaign_budget,
                campaign.start_date,
                campaign.end_date,
                campaign_budget.amount_micros
            FROM campaign
            WHERE campaign.id = {campaign_id}
        """
        ga_service = self.client.get_service("GoogleAdsService")
        response = ga_service.search(customer_id=customer_id, query=query)
        rows = list(response)
        if not rows:
            return {}
        row = rows[0]
        c = row.campaign
        return {
            "campaign_id": str(c.id),
            "name": c.name,
            "status": c.status.name,
            "campaign_type": c.advertising_channel_type.name,
            "campaign_budget": c.campaign_budget,
            "start_date": c.start_date,
            "end_date": c.end_date,
            "daily_budget_micros": row.campaign_budget.amount_micros,
        }

    def list(self, customer_id: str, page_size: int = 50) -> list[dict]:
        customer_id = normalize_customer_id(customer_id)
        query = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign.campaign_budget
            FROM campaign
            WHERE campaign.status != 'REMOVED'
            ORDER BY campaign.name
        """
        ga_service = self.client.get_service("GoogleAdsService")
        response = ga_service.search(customer_id=customer_id, query=query)
        results = []
        for row in response:
            c = row.campaign
            results.append(
                {
                    "campaign_id": str(c.id),
                    "name": c.name,
                    "status": c.status.name,
                    "campaign_type": c.advertising_channel_type.name,
                    "budget_resource_name": c.campaign_budget,
                }
            )
        return results

    def update(
        self, customer_id: str, campaign_id: str, req: UpdateCampaignRequest
    ) -> dict:
        customer_id = normalize_customer_id(customer_id)
        campaign_rn = self.campaign_svc.campaign_path(customer_id, campaign_id)

        op = self.client.get_type("CampaignOperation")
        campaign = op.update
        campaign.resource_name = campaign_rn
        update_mask_fields: list[str] = []

        if req.name is not None:
            campaign.name = req.name
            update_mask_fields.append("name")
        if req.status is not None:
            campaign.status = self.client.enums.CampaignStatusEnum[req.status.value]
            update_mask_fields.append("status")
        if req.start_date is not None:
            campaign.start_date = req.start_date
            update_mask_fields.append("start_date")
        if req.end_date is not None:
            campaign.end_date = req.end_date
            update_mask_fields.append("end_date")

        from google.protobuf import field_mask_pb2
        op.update_mask.CopyFrom(
            field_mask_pb2.FieldMask(paths=update_mask_fields)
        )

        try:
            resp = self.campaign_svc.mutate_campaigns(
                customer_id=customer_id, operations=[op]
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)

        return {"resource_name": resp.results[0].resource_name, "updated_fields": update_mask_fields}

    def remove(self, customer_id: str, campaign_id: str) -> dict:
        customer_id = normalize_customer_id(customer_id)
        campaign_rn = self.campaign_svc.campaign_path(customer_id, campaign_id)

        op = self.client.get_type("CampaignOperation")
        op.remove = campaign_rn

        try:
            resp = self.campaign_svc.mutate_campaigns(
                customer_id=customer_id, operations=[op]
            )
        except GoogleAdsException as exc:
            handle_google_ads_exception(exc)

        return {"removed": resp.results[0].resource_name}

    # ── Internal bidding helper ───────────────────────────────────────────────

    def _apply_bidding(self, campaign, req: CreateCampaignRequest) -> None:
        bst = req.bidding_strategy_type
        enums = self.client.enums

        if bst == BiddingStrategyType.MANUAL_CPC:
            campaign.manual_cpc.enhanced_cpc_enabled = req.enhanced_cpc_enabled

        elif bst == BiddingStrategyType.ENHANCED_CPC:
            campaign.manual_cpc.enhanced_cpc_enabled = True

        elif bst == BiddingStrategyType.MAXIMIZE_CLICKS:
            mc = campaign.maximize_clicks
            if req.cpc_bid_ceiling_micros:
                mc.cpc_bid_ceiling_micros = req.cpc_bid_ceiling_micros

        elif bst == BiddingStrategyType.MAXIMIZE_CONVERSIONS:
            campaign.maximize_conversions.target_cpa_micros = (
                req.target_cpa_micros or 0
            )

        elif bst == BiddingStrategyType.TARGET_CPA:
            if not req.target_cpa_micros:
                raise ValueError("target_cpa_micros required for TARGET_CPA.")
            campaign.target_cpa.target_cpa_micros = req.target_cpa_micros

        elif bst == BiddingStrategyType.TARGET_ROAS:
            if not req.target_roas:
                raise ValueError("target_roas required for TARGET_ROAS.")
            campaign.target_roas.target_roas = req.target_roas

        elif bst == BiddingStrategyType.TARGET_IMPRESSION_SHARE:
            tis = campaign.target_impression_share
            loc = req.target_impression_share_location or ImpressionShareLocation.ANYWHERE
            tis.location = enums.TargetImpressionShareLocationEnum[loc.value]
            if req.target_impression_share_fraction is not None:
                tis.location_fraction_micros = int(
                    req.target_impression_share_fraction * 1_000_000
                )
            if req.cpc_bid_ceiling_micros:
                tis.cpc_bid_ceiling_micros = req.cpc_bid_ceiling_micros

        elif bst == BiddingStrategyType.PORTFOLIO:
            if not req.portfolio_bidding_strategy_id:
                raise ValueError(
                    "portfolio_bidding_strategy_id required for PORTFOLIO type."
                )
            bs_svc = self.client.get_service("BiddingStrategyService")
            # Derive customer_id from the service — stored on the campaign object
            campaign.bidding_strategy = bs_svc.bidding_strategy_path(
                campaign.resource_name.split("/")[1],
                req.portfolio_bidding_strategy_id,
            )
